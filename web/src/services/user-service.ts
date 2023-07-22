export class UserService {
  liked_items: string[]

  constructor () {
    this.liked_items = []
  }

  like (item: string) {
    this.liked_items.push(item)
  }
}
