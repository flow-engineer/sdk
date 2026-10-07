/** One page of a list. `nextPage()` fetches the following one in the list's order. */
export interface Page<T> {
  data: T[];
  has_more: boolean;
  /** The next page, or `null` when `has_more` is false. */
  nextPage(): Promise<Page<T> | null>;
}

type Fetcher<T> = (after: string | undefined) => Promise<{ data: T[]; has_more: boolean }>;

/**
 * What every list method returns. Await it for the first page, or iterate it with
 * `for await` to walk every item across pages (cursor pagination with `after`).
 *
 * ```ts
 * const page = await flow.conversations.list({ limit: 10 });
 * for await (const conv of flow.conversations.list()) console.log(conv.id);
 * ```
 */
export class PagePromise<T extends { id: string }> implements PromiseLike<Page<T>>, AsyncIterable<T> {
  private first: Promise<Page<T>> | undefined;

  constructor(
    private readonly fetchPage: Fetcher<T>,
    private readonly startAfter?: string,
  ) {}

  private load(after: string | undefined): Promise<Page<T>> {
    return this.fetchPage(after).then((res) => {
      const page: Page<T> = {
        data: res.data,
        has_more: res.has_more,
        nextPage: () => {
          const last = res.data[res.data.length - 1];
          return res.has_more && last ? this.load(last.id) : Promise.resolve(null);
        },
      };
      return page;
    });
  }

  private firstPage(): Promise<Page<T>> {
    this.first ??= this.load(this.startAfter);
    return this.first;
  }

  then<R1 = Page<T>, R2 = never>(
    onfulfilled?: ((value: Page<T>) => R1 | PromiseLike<R1>) | null,
    onrejected?: ((reason: unknown) => R2 | PromiseLike<R2>) | null,
  ): Promise<R1 | R2> {
    return this.firstPage().then(onfulfilled, onrejected);
  }

  catch<R = never>(onrejected?: ((reason: unknown) => R | PromiseLike<R>) | null): Promise<Page<T> | R> {
    return this.firstPage().catch(onrejected);
  }

  async *[Symbol.asyncIterator](): AsyncIterator<T> {
    let page: Page<T> | null = await this.firstPage();
    while (page) {
      for (const item of page.data) yield item;
      page = await page.nextPage();
    }
  }

  /** Collects every item (up to `limit`) into an array. */
  async toArray(limit = Infinity): Promise<T[]> {
    const out: T[] = [];
    for await (const item of this) {
      if (out.length >= limit) break;
      out.push(item);
    }
    return out;
  }
}
