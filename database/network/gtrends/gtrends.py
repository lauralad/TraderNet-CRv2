import pandas as pd
from datetime import date
from pytrends.request import TrendReq
from database.entities.crypto import Crypto
from database.network.network import DatasetDownloader
import time


class GoogleTrendsDownloader(DatasetDownloader):
    def __init__(self, verbose: bool = True):
        super().__init__(date_column_name='date', verbose=verbose)
        self.trends_df_list = []

    def _download_year_trends(self, keyword: str, year: int) -> pd.DataFrame:
        today = date.today()

        if year == today.year:
            month_end = today.month
            day_end = today.day
        else:
            month_end = 12
            day_end = 31

        attempts = 0
        while attempts < 5:
            try:
                pytrends = TrendReq()
                pytrends.build_payload([keyword], timeframe=f"{year}-01-01 {year}-{month_end}-{day_end}")
                data = pytrends.interest_over_time().reset_index().drop_duplicates(subset='date')
                return data
            except TooManyRequestsError:
                # print(f"Request failed with exception {e}. Sleeping for {2 ** attempts} seconds.")
                time.sleep(2 ** attempts)  # Exponential backoff
                attempts += 1
                if attempts < 5:
                    self.trends_df_list = []  # Clear the list if an attempt fails
        raise Exception("Failed to download data after several attempts")
        # pytrends = TrendReq()
        # pytrends.build_payload([keyword], timeframe=f"{year}-01-01 {year}-{month_end}-{day_end}")
        # time.sleep(60)
        # data = pytrends.interest_over_time()
        # return data.reset_index().drop_duplicates(subset='date')
        # return TrendReq().get_historical_interest(
        #     keywords=[keyword],
        #     year_start=year,
        #     month_start=1,
        #     day_start=1,
        #     hour_start=0,
        #     year_end=year,
        #     month_end=month_end,
        #     day_end=day_end,
        #     hour_end=23
        # ).reset_index().drop_duplicates(subset=self.date_column_name)

    def download_historical_data(self, crypto: Crypto, history_filepath: str) -> bool:
        if self.verbose:
            print(f'Downloading {crypto.name} trends. It might take some time...')

        trends_df_list = []
        today_year = date.today().year
        for year in range(crypto.start_year, today_year + 1):
            # trends_df_list.append(self._download_year_trends(keyword=crypto.name, year=year))
            yearly_data = self._download_year_trends(keyword=crypto.name, year=year)
            self.trends_df_list.append(yearly_data)

        trends_df = pd.concat(self.trends_df_list, ignore_index=True)
        trends_df.drop_duplicates(subset='date', inplace=True)  # Ensure no duplicates
        # self._store_dataset(trends_df, history_filepath, ['date', crypto.name])

        # trends_df = pd.concat(trends_df_list, ignore_index=True)

        super()._store_dataset(
            dataset_df=trends_df,
            filepath=history_filepath,
            columns=[self.date_column_name, crypto.name]
        )
        return True

    def update_historical_data(self, crypto: Crypto, history_filepath: str) -> bool:
        if self.verbose:
            print(f'Updating {crypto.name} trends history')

        current_year = date.today().year
        history_df = pd.read_csv(history_filepath)
        history_df = history_df[history_df[self.date_column_name] < str(current_year)]
        latest_df = self._download_year_trends(keyword=crypto.name, year=current_year)
        merged_df = pd.concat((history_df, latest_df), ignore_index=True)
        merged_df.drop_duplicates(subset=self.date_column_name, inplace=True)

        assert not merged_df.duplicated(subset=self.date_column_name).any(), \
            'AssertionError: Duplicates found on Google Trends dates'

        super()._store_dataset(
            dataset_df=merged_df,
            filepath=history_filepath,
            columns=[self.date_column_name, crypto.name]
        )
        return True
