#!/usr/bin/env python
# coding: utf-8

# # Create Lookup Table from American English Nickname Collection

# In[1]:


import pandas as pd

AMERICAN_ENGLISH_NICKNAMES = ("./American_English_Nicknames.csv")
LOOKUP_OUTPUT = ("./nickname_lookup.csv")

# Constants calibrate the degree of specificity in matching names to groups
MIN_COND_PROB = 0.3
MIN_NAME_GROUP_COUNT = 5
MIN_NAME_GROUP_LEN = 3


# ## Intake CSV

# In[2]:


# For our purposes, the aliases represent commonly shared name groupings
raw_df = pd.read_csv(AMERICAN_ENGLISH_NICKNAMES, keep_default_na=False, na_values=[""])
df = raw_df.copy()
df = df.rename(columns={"NAME": "raw_name", "ALIAS": "name_group", "CAP": "cond_prob"})
df = df[["raw_name", "name_group", "cond_prob"]]
df = df.sort_values(["name_group", "raw_name"])


# ## Ensure names have zero spaces

# In[3]:


# Filter to exclude names with spaces
# For the linkage we will only use the first part of the first name
# Any additional words will be moved to the front of the middle name
multi_word_names = df["raw_name"].str.contains(" ")
df = df[~multi_word_names]
# And we'll remove spaces from aliases as well
df["name_group"] = df["name_group"].str.replace(" ", "")


# ## Exclude very short name groups

# In[4]:


# E.g., 'De', 'Un', 'Ki' -- these are typically paired with another
very_short_nicknames = (df["name_group"].str.len() < MIN_NAME_GROUP_LEN)
df = df[~very_short_nicknames]


# ## Exclude rarely linked name groups

# In[5]:


df["group_n"] = df.groupby("name_group")["name_group"].transform("count")
df = df[df["group_n"] >= MIN_NAME_GROUP_COUNT]


# ## Exclude unlikely name<->group pairings

# In[6]:


probable_name_groups = df["cond_prob"] >= MIN_COND_PROB
df = df[probable_name_groups]


# ## Select the best name<->group links

# In[7]:


# Take only the top rank of cumulative name_group probability (cond_prob)
#   cond_prob = p of name_group being used to denote a given name,
#   i.e., count(name_group[i]^name[j])/count(name[j])
df = df[df.groupby("raw_name")["cond_prob"].rank(ascending=False) == 1]


# ## Handle loops

# In[8]:


# Loops form when, e.g., CHRIS -> CHRISTOPHER and CHRISTOPHER -> CHRIS
# It doesn't matter which of the values we choose, but we must resolve these loops to one
loops = df.merge(
    df, "inner", left_on=["raw_name", "name_group"], right_on=["name_group", "raw_name"]
)
loop_priority = loops[loops["group_n_y"] >= loops["group_n_x"]]

# Convert the loop_priority into a replacement dict and apply it to df
loop_resolver = dict(
    loop_priority[["raw_name_y", "name_group_y"]].to_dict(orient="split")["data"]
)
df["name_group"] = df["name_group"].replace(loop_resolver)


# ## Collapse chains

# In[9]:


# Remove cases where the name is now equal to the name_group
# e.g., what was once CHRIS -> CHRISTOPHER is now CHRISTOPHER -> CHRISTOPHER
unnecessary_equalities = df["raw_name"] == df["name_group"]
df = df[~unnecessary_equalities]

# Shorten chains
# e.g., BACKY -> BECKY becomes BACKY -> REBECCA when BECKY -> REBECCA exists
for _ in range(10):
    chains = df.merge(df, "inner", left_on=["name_group"], right_on=["raw_name"])
    if chains.empty:
        break
    chain_resolver = dict(
        chains[["raw_name_x", "name_group_y"]].to_dict(orient="split")["data"]
    )
    df["name_group"] = df["raw_name"].map(chain_resolver).fillna(df["name_group"])


# ## Run sanity checks

# In[10]:


# No spaces in incoming names
assert not df["raw_name"].str.contains(" ").any()

# No spaces in outgoing name_groups
assert not df["name_group"].str.contains(" ").any()

# No rows lower than our minimum cond_prob threshhold
assert (df["cond_prob"] >= MIN_COND_PROB).all()

# No rows lower than our minimum name_group count threshhold
assert (df["group_n"] >= MIN_NAME_GROUP_COUNT).all()

# No rows lower than our minimum name_group length
df["name_group_len"] = df["name_group"].str.len()
assert (df["name_group_len"] >= MIN_NAME_GROUP_LEN).all()

# All chains have been shortened
all_chains = df.merge(df, "inner", left_on=["name_group"], right_on=["raw_name"])
assert all_chains.empty

# All loops have been resolved (this is also covered by chains being shortened)
all_loops = df.merge(
    df, "inner", left_on=["raw_name", "name_group"], right_on=["name_group", "raw_name"]
)
assert all_loops.empty

print('No apparent problems.')


# ## Write to CSV

# In[11]:


# Make a final implementation version
final_df = df[["raw_name", "name_group"]].apply(lambda x: x.str.lower())
final_df = final_df.sort_values(["raw_name", "name_group"])
final_df.to_csv(LOOKUP_OUTPUT, index=False)

print('Complete.')
final_df.sample(20)


# ## Validate final DataFrame via known hash

# In[12]:


import hashlib 

IRIS_COMPUTED_HASH = 'ba62eb00e11056ebe60550db621cf8546db77be2ddcf062a903e89fac33dc4ae'

final_df_hash = hashlib.sha256(pd.util.hash_pandas_object(final_df).values).hexdigest() 

assert final_df_hash == IRIS_COMPUTED_HASH, 'This final lookup table does not match existing builds.'
print('Good: this final lookup table looks identical to the existing build at IRIS.')

