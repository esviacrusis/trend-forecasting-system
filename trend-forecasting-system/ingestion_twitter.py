################################################################################
# Module    :   This is part of the data ingestion script to get data from 
#               Twitter API and store it in the database
# Author    :   Eric S. Viacrusis 
# Date      :   March 27, 2026
#
# UPDATES   
# March 27, 2026 - save the data from Twitter API to the database
###############################################################################

# read csv file 

import pandas as pd
import csv

# with open('xposts.csv', 'r') as file:
#    reader = csv.reader(file)
#    for row in reader:
#        print(row)

df = pd.read_csv('/Users/eric/Documents/CSUEB Subjects/2026 Spring /BAN 693 Capstone/Codes/Twitter /xposts.csv')
print(df.head(10))



# sample twitter data 
# @voguemagazine

twitter_post = """
To trace @DojaCat’s rise is, in some ways, to chart the tangled relationship between the music industry and the internet. Long before she became the third-best-selling female rapper of all time, she was a keenly creative (and very online) teenager, rapping over beats she found on YouTube and SoundCloud. Later, platforms like TikTok, Twitch, and X would help her forge a striking intimacy with her fans, known as the “Kittenz.”
But lately, the 30-year-old rapper has been taking care of herself, both physically and mentally. Doja credits therapy for allowing her “to see through a lot of the fog that I couldn’t see through before,” and her close-knit entourage—including her managers, her creative director, and members of her glam squad—for “understanding” her totally. One result of all that clarity? The success of her globe-circling, nearly year-long arena tour, supporting her fifth studio album, “Vie,” an artful pastiche of 1980s R&B, funk, and commanding power pop. Welcome to Doja’s new era.
For Vogue’s April 2026 issue, Liam Hess meets Doja between shows in Sydney to talk about failure, fandom, and fashion. Tap the link in our bio to read the full profile. 
https://vogue.com/article/doja-cat-april-cover-2026-interview
"""

# A. Post-level data (core record)
post_id = ""
author_id = ""
username = ""
text = ""
language = ""
post_type = ""
is_reply = ""


# B. Engagement metrics"
like_count = ""
repost_count = ""
reply_count = ""
quote_count = ""

# C. Content / metadata (for NLP later)
hashtags = ""
mentioned_accounts = ""
media_urls = ""
attachments_media_keys = ""


# save the data to the s3 bucket and then to the database (to be implemented)