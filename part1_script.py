# Author: Johannes Willmann
# Date: 2020-06-19

import datetime
import doctest
from fpdf import FPDF
from functools import reduce
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import wbdata


INDICATOR = "SH.STA.BASS.ZS"


def generate_part1_output(indicator):
    """
    Generates the one pager containing the chart and paragraph to answer
    the questions about the proposed World Development Indicator (WDI).
    """
    indicator_data = retrieve_data_from_api(indicator)
    income_level_mapping = create_country_income_level_mapping()
    df = join_income_level_to_indicator(indicator_data, income_level_mapping)
    create_chart(df)
    create_document()


def retrieve_data_from_api(indicator):
    """
    Calls wbdata API client to retrieve WDI data and returns data as Pandas dataframe.
 
    >>> VALID_INDICATOR = 'SH.STA.BASS.ZS'
    >>> INVALID_INDICATOR = 'foo'

    >>> type(retrieve_data_from_api(VALID_INDICATOR))
    <class 'pandas.core.frame.DataFrame'>

    >>> retrieve_data_from_api(INVALID_INDICATOR)
    This indicator could not be retrieved.
    """
    min_date = datetime.datetime(1960, 1, 1)
    max_date = datetime.datetime(2020, 1, 1)
    data_date = (min_date, max_date)

    try:
        return wbdata.get_dataframe(
            {indicator: "value"}, data_date=data_date
        ).reset_index()
    except:
        print("This indicator could not be retrieved.")


def create_country_income_level_mapping():
    """
    Creates a mapping table for countries and their respective income levels.

    >>> create_country_income_level_mapping().query("country in ['Aruba', 'Afghanistan']")
        id iso2Code      country income_level
    0  HIC       AW        Aruba  High income
    1  LIC       AF  Afghanistan   Low income
    """

    country_information = retrieve_country_information_from_wb_api()

    return reduce(
        lambda accu, func: func(accu),
        [
            create_dataframe_from_country_information,
            filter_out_non_country_observations,
            rename_and_select_relevant_columns,
        ],
        country_information,
    )


def retrieve_country_information_from_wb_api():
    """
    Retrieves country information, such as income levels, from World Bank API.

    >>> [x['incomeLevel'] for x in retrieve_country_information_from_wb_api() if x.get('id') =='ABW']
    [{'id': 'HIC', 'value': 'High income'}]
    """
    return wbdata.search_countries("", display=False)


def create_dataframe_from_country_information(country_information):
    """
    Converts list of nested dictionaries with country information retrieved from World Bank API into
    Pandas dataframe.

    >>> country_information = [
    ...     {'name':'Aruba', 'incomeLevel':{'id': 'HIC', 'value': 'High income'}},
    ...     {'name':'Afghanistan','incomeLevel':{'id': 'LIC', 'value': 'Low income'}}]

    >>> create_dataframe_from_country_information(country_information)
              name   id        value
    0        Aruba  HIC  High income
    1  Afghanistan  LIC   Low income
    """
    return pd.DataFrame([{**x, **x.pop("incomeLevel")} for x in country_information])


def filter_out_non_country_observations(df):
    """
    Filters out aggregates of countries (e.g. 'Europe & Central Asia (IBRD-only countries)' to only
    include single countries in analysis.)

    >>> df = pd.DataFrame({'name':['Aruba', 'East Asia & Pacific (IBRD-only countries)'], 'value':['High income', 'Aggregates']})

    >>> filter_out_non_country_observations(df)
        name        value
    0  Aruba  High income
    """
    return df.loc[df["value"] != "Aggregates", :]


def rename_and_select_relevant_columns(df):
    """
    Renames and selects the relevant columns.
    """
    return df.rename(columns={"name": "country", "value": "income_level"}).loc[
        :, ["id", "iso2Code", "country", "income_level"]
    ]


def join_income_level_to_indicator(indicator_data, income_level_mapping):
    """
    Joins the income group/country mapping table with the basic sanitation services
    dataframe.

    >>> indicator_data = pd.DataFrame({"country":["A", "B"], "value":[20, 90]})
    >>> income_level_mapping = pd.DataFrame({"country":["A", "B"], 
    ...     "income_level":["Low income", "High income"]})

    >>> join_income_level_to_indicator(indicator_data, income_level_mapping)
      country  value income_level
    0       A     20   Low income
    1       B     90  High income
    """
    return pd.merge(indicator_data, income_level_mapping, on="country", how="inner")


def create_chart(df):
    """
    Creates and stores a chart to answer the questions about the proposed World
    Development Indicator (WDI).
    """
    sns.set(style="whitegrid")
    # Plot the responses for different events and regions
    fig, ax = plt.subplots(1, figsize=(15, 9))
    sns.lineplot(
        x="date",
        y="value",
        hue="income_level",
        hue_order=[
            "High income",
            "Upper middle income",
            "Lower middle income",
            "Low income",
        ],
        palette=sns.dark_palette("navy", 4),
        data=df,
    )

    sns.lineplot(x="date", y="value", label="World", data=df)

    plt.xlabel("Date")
    plt.ylabel("People using at least basic sanitation services (% of population)")
    plt.title("People using at least basic sanitation services by income group")
    plt.savefig("plot.png")


def create_document():
    """
    Creates a Word document containing the chart and paragraph to answer
    the proposed questions about the proposed World Development Indicator.
    """

    DESCRIPTION_OF_PLOT = """
    To analyze changes and potential trends in the use of at least basic sanitation services (% of population), as well as the variance between income groups, I retrieved the relevant indicator from the World Bank API, transformed it into tabular form, joined information about a country's respective income level to the indicator data, and generated a chart from the combined indicator/income group data.

    The below chart displays the time range for which data was available via the API on the x-axis and the share of a population that is using at least basic sanitation services on the y-axis. The lines indicate the average share of the population using at least basic sanitation services by income group for a given point in time. The bands on either side of each line are confidence intervals.

    The chart indicates that the use in at least basic sanitation services has indeed been changing with a positive trend throughout all income groups. However, large differences between income groups can be observed in the indicator's level at the outset of the data collection period, as well as how severely it changed over the observation period. Countries associated with a high-income level have the highest share of their populations using at least basic sanitation services, while countries associated with a low-income level score lowest. Changes in the indicator are more prevalent for the middle- and lower-income countries, with countries classified as 'Lower middle income' increasing most. 
    """

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("arial", "B", 12)
    pdf.cell(40, 10, "Technical exercise for Data Scientist position (Part I)", 0, 2)
    pdf.set_font("arial", "", 10)
    pdf.multi_cell(w=0, h=5, txt=DESCRIPTION_OF_PLOT)
    pdf.image("plot.png", x=None, y=None, w=175, h=100, type="", link="")
    pdf.output("part1.pdf", "F")


if __name__ == "__main__":
    generate_part1_output(INDICATOR)
