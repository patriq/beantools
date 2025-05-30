import datetime

import click
import yfinance
from beancount import loader
from beancount.core import data
from beancount.scripts.format import align_beancount


class Price(object):
    base: str
    quote: str
    ticker: str
    date: datetime.date
    amount: float

    def __init__(self, base, quote, ticker, date=datetime.date.today(), amount=float('nan')):
        self.base = base
        self.quote = quote
        self.ticker = ticker
        self.date = date
        self.amount = amount

    def to_beancount(self):
        return "{} price {}\t{:.3f} {}".format(self.date.strftime('%Y-%m-%d'), self.base, self.amount, self.quote)

    def __str__(self):
        return self.to_beancount()

    __repr__ = __str__

    def __eq__(self, other):
        return isinstance(other, Price) and hash(self) == hash(other)

    def __hash__(self):
        return hash(self.base) + hash(self.quote) + hash(self.date)


def commodity_entry_to_price(entry: data.Commodity) -> Price:
    price = entry.meta['price'].replace("yahoo/", "").split(':')
    return Price(entry.currency, price[0], price[1])


def price_entry_to_price(entry: data.Price) -> Price:
    return Price(entry.currency, entry.amount.currency, None, entry.date, entry.amount.number)


def write_file(filename: str, contents: str):
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(contents)


def read_file_lines(filename: str) -> [str]:
    with open(filename, 'r', encoding='utf-8') as file:
        return file.readlines()


def load_file_skip_plugins(filename):
    """Loads a beancount file ignoring all plugin directives. This is done by commenting all lines
    starting with "plugin" before loading it to with beancount.loader.
    """

    def comment_plugin(line):
        if line.startswith("plugin"):
            return ';' + line
        return line

    contents = "".join(map(comment_plugin, read_file_lines(filename)))
    return loader.load_string(contents)


@click.command()
@click.argument('filename', type=click.Path(resolve_path=True, exists=True))
@click.option('--dry-run/--no-dry-run', default=False, help='Print instead of updating the file')
def main(filename, dry_run):
    entries, errors, options_map = load_file_skip_plugins(filename)

    # Find all commodity entries and extract their tickers
    commodity_entries = list(filter(lambda entry: isinstance(entry, data.Commodity) and 'price' in entry.meta, entries))

    # Find all price entries
    price_entries = list(filter(lambda entry: isinstance(entry, data.Price), entries))

    # Map all commodity and price entries to prices
    new_prices = set(map(commodity_entry_to_price, commodity_entries))
    existing_prices = set(map(price_entry_to_price, price_entries))

    # Fetch all new prices
    tickers = yfinance.Tickers(" ".join(map(lambda price: price.ticker, new_prices)))
    for price in new_prices:
        fast_info = tickers.tickers[price.ticker].fast_info
        # for date, price_data in fast_info._get_1y_prices()["Close"].loc['2025-02-19':'2025-04-03'].items():
        #     print(Price(price.base, price.quote, price.ticker, date, price_data).to_beancount())
        price.amount = fast_info.last_price

    # Deduplicate existing prices and sort them by date
    all_prices = sorted(list(existing_prices.difference(new_prices)) + list(new_prices), key=lambda x: (x.date, x.base))

    # Collect all the price entry lines of the original ledger, so we can filter them out
    price_entry_line_numbers = set(map(lambda entry: entry.meta['lineno'], price_entries))
    new_ledger_lines = []
    added_prices = False
    for index, line in enumerate(read_file_lines(filename)):
        if (index + 1) in price_entry_line_numbers:
            if not added_prices:
                new_ledger_lines.extend(map(lambda price: "{}\n".format(price.to_beancount()), all_prices))
                added_prices = True
        else:
            new_ledger_lines.append(line)
    new_ledger_contents = align_beancount("".join(new_ledger_lines))

    # Print or write to the file
    if dry_run:
        print(new_ledger_contents)
    else:
        write_file(filename, new_ledger_contents)


if __name__ == '__main__':
    main()
