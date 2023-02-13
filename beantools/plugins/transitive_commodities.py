"""A plugin that inserts additional price directives to help projecting all commodities to the ledger's operating currencies.
"""
from beancount.core import amount, data, prices

__plugins__ = ["generate_transitive_commodities"]

metadata = data.new_metadata('<{}>'.format(__file__), 0)

def generate_transitive_commodities(entries, options_map, config=None):
    # Grab operating commodities
    operating_currencies = options_map['operating_currency']

    # Grab price map from beancount
    # price_map = {('base_commodity', 'quote_commodity'): [(datetime.date, decimal), ...], ...}
    original_price_map = prices.build_price_map(entries)

    # Grab all commodities
    commodities = list(filter(lambda entry: isinstance(entry, data.Commodity), entries))

    # Project all commodities to all operating currencies
    price_map = original_price_map
    for operating_currency in operating_currencies:
        for commodity in commodities:
            price_map = prices.project(price_map, commodity.currency, operating_currency)

    # Generate price entries for all entries not found on the original price map
    additional_price_entries = []
    for (base_currency, quote_currency), price_list in price_map.items():
        if base_currency == quote_currency:
            continue

        if (base_currency, quote_currency) in original_price_map:
            continue


        if quote_currency not in operating_currencies:
            continue

        for (price_date, price_amount) in price_list:
            additional_price_entries.append(
                data.Price(metadata, price_date, base_currency, 
                    amount.Amount(round(price_amount, 2), quote_currency)))

    return entries + additional_price_entries, []