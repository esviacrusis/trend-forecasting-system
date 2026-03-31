##########################################################################
# Task 4.	TF-IDF 
##########################################################################

# Article titles grouped by month

articles_by_time = {
    "September 1": [
        "", 
        "", 
        ""
    ],    
    "September 7": [
        "blue, blue, red, red, white white",
        "yellow, yellow, red, red, fucshia, light blue",
        "red, orange, yellow, green, blue, indigo, violet"
    ],
    
    "September 14": [
        "white, champagne, light pink, light blue, light green",
        "black, white, gold, silver",
        "mahogany, maroon, burgundy, crimson, scarlet"
    ],
    
    "September 21": [
        "white, blue, light blue, aqua, cyan",
        "red, orange, yellow, green, navy, purple",
        "light blue, indigo, violet, lavender, lilac, magenta, black"
    ],

    "September 28": [
        "white, brown, maroon, blue, light blue, aqua, cyan",
        "red, orange, yellow, green, navy, purple",
        "light blue, indigo, violet, lavender, lilac, magenta, black"
    ],

    "October 7": [
        "white, blue, light blue, aqua, cyan, green, green",
        "red, orange, yellow, green, navy, purple, white, black, gold",
        "light blue, indigo, violet, lavender, lilac, magenta, black"
    ],

    "October 14": [
        "white, blue, light blue, aqua, cyan",
        "red, orange, yellow, green, navy, purple",
        "light blue, indigo, violet, lavender, lilac, magenta, black"
    ],

    "October 21": [
        "white, blue, light blue, aqua, cyan",
        "yellow, bronze, red, orange, yellow, green, navy, purple",
        "lilac, light blue, indigo, violet, lavender, lilac, magenta, black"
    ],

    "October 28": [
        "white, blue, burgundy, light blue, aqua, cyan",
        "gold, blue, red, orange, yellow, green, navy, purple",
        "light blue, magnolia, indigo, violet, lavender, lilac, magenta, black"
    ]

}


##### Item 1. Build a TF-IDF vocabulary across all titles ---------------------------------------#####

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np 

# put all titles together into one list 

all_titles = []
for titles in articles_by_time.values(): 
        for title in titles:
                all_titles.append(title)

# FOR CHECKING PURPOSES: print all titles
print(all_titles)


# build TF-IDF vocabulary across all titles
vectorizer = TfidfVectorizer(stop_words="english")
X = vectorizer.fit_transform(all_titles)

# print vocabulary
print("TF-IDF Vocabulary:")
print(vectorizer.vocabulary_)


##### Item 2. Compute the average TF-IDF vector per month.  -------------------------------------#####

# 1) Put all titles together and build one shared TF-IDF vocabulary
all_titles = []
for month_titles in articles_by_time.values():
    for title in month_titles:
        all_titles.append(title)

vectorizer = TfidfVectorizer(stop_words="english")
vectorizer.fit(all_titles)
terms = vectorizer.get_feature_names_out()

# FOR CHECKING PURPOSES: print the terms in the vocabulary
print(terms)

# 2) Compute average TF-IDF vector per month
tfidf_by_month = {}
for month, titles in articles_by_time.items():
    X_month = vectorizer.transform(titles)
    tfidf_by_month[month] = np.asarray(X_month.mean(axis=0)).flatten()

# print average TF-IDF vector per month
print("Average TF-IDF vector per month:")


from datetime import datetime

for month in sorted(tfidf_by_month.keys(), key=lambda x: datetime.strptime(x, "%B %d")):
    print(f"\nmonth: {month}")
    avg_vec = tfidf_by_month[month]
    for i, score in enumerate(avg_vec):
        if score > 0:
            print(f"{terms[i]}: {score:.3f}")

# 3) Compare each month to the previous month
months = sorted(tfidf_by_month.keys(), key=lambda x: datetime.strptime(x, "%B %d"))

for i in range(1, len(months)):
    prev_month = months[i - 1]
    curr_month = months[i]
    
    change = tfidf_by_month[curr_month] - tfidf_by_month[prev_month]
    
    # top 3 emerging topics = largest positive changes
    emerging_idx = change.argsort()[::-1]
    
    # top 3 diminishing topics = largest negative changes
    diminishing_idx = change.argsort()
    
    print(f"\n{'='*50}")
    print(f"Comparing {curr_month} vs {prev_month}")
    
    
    # EMERGING TOPICS 
    print("\nTop 3 emerging topic terms:")
    emerging_count = 0
    for idx in emerging_idx:
        if change[idx] > 0:
            print(f"{terms[idx]} ({change[idx]:.3f})")
            emerging_count += 1
        if emerging_count == 3:
            break
    # DIMINISHING TOPICS 
    print("\nTop 3 diminishing topic terms:")
    diminishing_count = 0
    for idx in diminishing_idx:
        if change[idx] < 0:
            print(f"{terms[idx]} ({change[idx]:.3f})")
            diminishing_count += 1
        if diminishing_count == 3:
            break

##### Item 2. Visualization  ---------------------------------------------------------------#####

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import matplotlib.pyplot as plt

# Article titles grouped by month
articles_by_time = {
    "September 1": [
        "", 
        "", 
        ""
    ],    
    "September 7": [
        "blue, blue, red, red, white white",
        "yellow, yellow, red, red, fucshia, light blue",
        "red, orange, yellow, green, blue, indigo, violet"
    ],
    
    "September 14": [
        "white, champagne, light pink, light blue, light green",
        "black, white, gold, silver",
        "mahogany, maroon, burgundy, crimson, scarlet"
    ],
    
    "September 21": [
        "white, blue, light blue, aqua, cyan",
        "red, orange, yellow, green, navy, purple",
        "light blue, indigo, violet, lavender, lilac, magenta, black"
    ],

    "September 28": [
        "white, brown, maroon, blue, light blue, aqua, cyan",
        "red, orange, yellow, green, navy, purple",
        "light blue, indigo, violet, lavender, lilac, magenta, black"
    ],

    "October 7": [
        "white, blue, light blue, aqua, cyan, green, green",
        "red, orange, yellow, green, navy, purple, white, black, gold",
        "light blue, indigo, violet, lavender, lilac, magenta, black"
    ],

    "October 14": [
        "white, blue, light blue, aqua, cyan",
        "red, orange, yellow, green, navy, purple",
        "light blue, indigo, violet, lavender, lilac, magenta, black"
    ],

    "October 21": [
        "white, blue, light blue, aqua, cyan",
        "yellow, bronze, red, orange, yellow, green, navy, purple",
        "lilac, light blue, indigo, violet, lavender, lilac, magenta, black"
    ],

    "October 28": [
        "white, blue, burgundy, light blue, aqua, cyan",
        "gold, blue, red, orange, yellow, green, navy, purple",
        "light blue, magnolia, indigo, violet, lavender, lilac, magenta, black"
    ]

}
# Step 1: Combine all titles to build TF-IDF vocabulary
all_titles = [title for titles in articles_by_time.values() for title in titles]

vectorizer = TfidfVectorizer(stop_words="english")
vectorizer.fit(all_titles)

terms = vectorizer.get_feature_names_out()

# Step 2: Compute average TF-IDF per month
tfidf_by_month = {}
for month, titles in articles_by_time.items():
    X = vectorizer.transform(titles)
    tfidf_by_month[month] = np.asarray(X.mean(axis=0)).flatten()

# Sort months
from datetime import datetime

months = sorted(tfidf_by_month.keys(), key=lambda x: datetime.strptime(x, "%B %d"))

# Step 3: Create matrix ordered by months
tfidf_matrix = np.array([tfidf_by_month[y] for y in months])

# Step 4: Select terms with largest variation across months
variances = tfidf_matrix.var(axis=0)
top_indices = variances.argsort()[::-1][:6]   # choose top 6 changing terms

# Step 5: Plot line graph
plt.figure()

for idx in top_indices:
    values = [tfidf_by_month[y][idx] for y in months]
    plt.plot(months, values, marker='o', label=terms[idx])

plt.title("TF-IDF Color Trends Over Time")
plt.xlabel("Weeks")
plt.ylabel("Average TF-IDF Value")

plt.legend()
plt.tight_layout()
plt.show()

