# import pandas as pd
# from gdeltdoc import GdeltDoc, Filters
# from datetime import datetime, timedelta
# import time
# # Function to fetch and store data
# def fetch_news_to_csv(country, start_date, end_date, csv_file_name):
#     # Initialize GDELT client
#     gd = GdeltDoc()
#     # Format filters correctly
#     filters = Filters(
#         keyword=["currency","forex","finance","disease","war","election","pandemic","inflation","bank","trade","treaty"],
#         start_date=start_date,  # Use the string date format
#         end_date=end_date,      # Use the string date format
#         country=country         # Use country code
#     )
#     try:
#         print(f"Fetching news from {start_date} to {end_date}...")
#         # Fetch articles for the given date range
#         articles = gd.article_search(filters)
#         print(type(articles))
#         # Check if articles are returned and are in DataFrame format
#         if not articles.empty:  # Check if DataFrame is not empty
#             # Add a column for the date
#             articles["date"] = start_date
#             # Append to CSV (create a new file if it doesn't exist)
#             if not pd.io.common.file_exists(csv_file_name):
#                 articles.to_csv(csv_file_name, mode="w", index=False, header=True)
#             else:
#                 articles.to_csv(csv_file_name, mode="a", index=False, header=False)
#             print(f"Appended {len(articles)} articles to {csv_file_name}.")
#         else:
#             print(f"No valid articles found for date: {start_date}.")
#     except Exception as e:
#         print(f"Error fetching data from {start_date} to {end_date}: {e}")
# # Define the start and end dates
# start = datetime(2020, 1, 22)
# end = datetime(2020, 1, 23)
# # Loop through each day in the date range
# current_date = start
# while current_date < end:
#     # Check if the current date is the 30th and pause for 5 seconds
#     if current_date.day == 30:
#           time.sleep(5)
#     # Set the next day as the end date for the current date
#     next_day = current_date + timedelta(days=1)
#     # Format the current date and next day as strings in "YYYY-MM-DD" format
#     current_date_str = current_date.strftime("%Y-%m-%d")
#     next_day_str = next_day.strftime("%Y-%m-%d")
#     # Fetch and store the news data for the day
#     fetch_news_to_csv(
#         country="UK",
#         start_date=current_date_str,
#         end_date=next_day_str,
#         csv_file_name="news_data_IN.csv"
#     )
#     # Move to the next day
#     current_date += timedelta(days=1)
# print("Data fetching completed.")