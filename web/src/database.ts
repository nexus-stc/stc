import Dexie from 'dexie'
import { MetaDb } from 'summa-wasm'

import { average } from '@/utils'

export class UserDb extends Dexie {
  bookmarks!: Dexie.Table<IBookmark, [string, string]>
  search_metrics!: Dexie.Table<ISearchMetric, []>

  constructor (name: string, version: number) {
    super(name)
    this.version(version).stores({
      bookmarks: '[index_name+query],created_at',
      search_metrics: 'created_at'
    })
    this.bookmarks.mapToClass(Bookmark)
    this.search_metrics.mapToClass(SearchMetric)
  }

  async add_search_metrics (search_metrics: SearchMetric) {
    return await this.transaction('rw', this.search_metrics, async () => {
      await this.search_metrics.offset(100).delete()
      return await this.search_metrics.put(search_metrics)
    })
  }

  async get_average_spent (last_n_time: number) {
    return await this.transaction('rw', this.search_metrics, async () => {
      const result = await this.search_metrics
        .orderBy('created_at')
        .reverse()
        .limit(last_n_time)
        .toArray()
      if (result.length < last_n_time) {
        return undefined
      }
      return average(result.map((x) => x.spent))
    })
  }

  async add_bookmark (bookmark: IBookmark) {
    return await this.transaction('rw', this.bookmarks, async () => {
      return await this.bookmarks.put(bookmark)
    })
  }

  async get_all_bookmarks () {
    return await this.transaction('rw', this.bookmarks, async () => {
      return await this.bookmarks.orderBy('created_at').reverse().toArray()
    })
  }

  async has_bookmark (index_name: string, query: string) {
    return await this.transaction('rw', this.bookmarks, async () => {
      return (await this.bookmarks.get([index_name, query])) !== undefined
    })
  }

  async delete_bookmark (index_name: string, query: string) {
    await this.transaction('rw', this.bookmarks, async () => {
      await this.bookmarks.delete([index_name, query])
    })
  }
}

interface IBookmark {
  index_name: string
  query: string
  created_at: number
}

export class Bookmark implements IBookmark {
  index_name: string
  query: string
  created_at: number

  constructor (index_name: string, query: string) {
    this.index_name = index_name
    this.query = query
    this.created_at = Date.now() / 1000
  }
}

interface ISearchMetric {
  spent: number
  created_at: number
}

export class SearchMetric implements ISearchMetric {
  spent: number
  created_at: number

  constructor (spent: number) {
    this.spent = spent
    this.created_at = Date.now() / 1000
  }
}

export const meta_db = new MetaDb('MetaDb', 8)
export const user_db = new UserDb('UserDb', 8)
