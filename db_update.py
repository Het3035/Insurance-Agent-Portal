from db import policies_collection

policies_collection.update_many(
    {"remaining_sum_insured": {"$exists": False}},
    [
        {"$set": {"remaining_sum_insured": "$sum_insured"}}
    ]
)

print("Old policies fixed")