/**
 * @desc downloadProgress initiator
 * @param files {Array}
 * @event beforeLoading
 * @event afterLoading
 * @event progress
 * @return {downloadProgressObject}
 **/
export default class DownloadProgress {
  /**
   * @desc downloadProgress constructor
   * @param files {Array}
   **/
  files: string[]
  percentages: {}
  percentage: number
  events: {
    beforeLoading: Event
    afterLoading: any
    progress: any
  }

  promises: Array<Promise<any>>

  constructor (files) {
    this.files = files
    this.percentages = {}
    this.percentage = 0
    this.events = {
      beforeLoading: new Event('beforeLoading'),
      afterLoading: function (response, url) {
        return new CustomEvent('afterLoading', {
          detail: { response, url }
        })
      },
      progress: function (percentage) {
        return new CustomEvent('progress', { detail: percentage })
      }
    }
    this.promises = []
  }

  /**
   * @desc the callback that gets called on update progress
   * @param url {String}
   * @param oEvent {Object}
   **/
  _downloadProgressUpdateProgress (url, oEvent) {
    const percentComplete = oEvent.lengthComputable
      ? oEvent.loaded / oEvent.total
      : oEvent.loaded /
        (oEvent.target.getResponseHeader('x-decompressed-content-length') || oEvent.target.getResponseHeader('content-length'))
    let totalPercentage = 0
    let key
    this.percentages[url] = percentComplete
    for (key in this.percentages) {
      totalPercentage += this.percentages[key]
    }
    this.percentage = (totalPercentage / this.files.length) * 100
    document.dispatchEvent(this.events.progress(this.percentage))
  }

  /**
   * @desc gets the target file and sends the responseText back
   * @param index {Number}
   **/
  async initiate_download (index) {
    const that = this
    return await new Promise(function (resolve, reject) {
      const xhr = new XMLHttpRequest()
      const url = that.files[index]
      xhr.addEventListener(
        'progress',
        that._downloadProgressUpdateProgress.bind(that, url)
      )
      xhr.responseType = "arraybuffer";
      xhr.open('GET', url)
      xhr.onreadystatechange = function (index) {
        if (xhr.status === 200 && xhr.readyState === 4) {
          document.dispatchEvent(
            that.events.afterLoading(xhr.response, that.files[index])
          )
        }
      }.bind(that, index)
      xhr.onload = function () {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(xhr.response)
        } else {
          reject({
            status: xhr.status,
            statusText: xhr.statusText
          })
        }
      }
      xhr.onerror = function () {
        reject({
          status: xhr.status,
          statusText: xhr.statusText
        })
      }
      xhr.send()
    })
  }

  /**
   * @desc attaches the callback to the given even
   * @param event {Object}
   * @param callback {Function}
   * @return {downloadProgressObject}
   **/
  on (event, callback) {
    document.addEventListener(event, callback, false)
    return this
  }

  /**
   * @desc initializes the loading
   * @return {downloadProgressObject}
   **/
  init () {
    document.dispatchEvent(this.events.beforeLoading)
    let i = 0
    for (; i < this.files.length; i++) {
      this.percentages[this.files[i]] = 0
      this.promises.push(this.initiate_download(i))
    }
    return this
  }
}

export async function tracked_download (files, progress_bar) {
  const dp = new DownloadProgress(files)
  dp.on('progress', function (e) {
    let downloaded = e.detail
    if (e.detail === Infinity) {
      downloaded = 0
    }

    progress_bar.value = `${downloaded.toFixed(0)}%`
  }).on('afterLoading', function () {
    progress_bar.value = undefined
  })
  dp.init()
  return await Promise.all(dp.promises)
}
