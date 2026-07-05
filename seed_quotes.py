from db import icici_quotes, new_india_quotes, tata_quotes

icici_quotes.delete_many({})
new_india_quotes.delete_many({})
tata_quotes.delete_many({})

age_bands = [
    (0,17),(18,30),(31,35),(36,40),(41,45),
    (46,50),(51,55),(56,60),(61,65),(66,99)
]

premium_table = {
    500000:  [4279,6094,7370,9301,12238,14652,18887,21318,28870,32648],
    1000000: [5247,7486,9070,11457,15081,18062,23298,26301,35629,40299],
    1500000: [6529,9334,11314,14306,18843,22578,29134,32890,44578,50424],
    2500000: [8773,12573,15252,19294,25438,30492,39358,44446,60253,68162],
    5000000: [12194,17501,21247,26895,35486,42548,54940,62046,84145,95194],
    7500000: [13789,19800,24041,30437,40167,48164,62194,70246,95271,107789],
    10000000:[14916,21428,26026,32951,43489,52146,67348,76065,103169,116727]
}

for si, premiums in premium_table.items():
    for i,(min_age,max_age) in enumerate(age_bands):
        base = premiums[i]

        new_india_quotes.insert_one({
            "min_age":min_age,"max_age":max_age,"si":si,"premium":base
        })
        icici_quotes.insert_one({
            "min_age":min_age,"max_age":max_age,"si":si,"premium":round(base*0.88,2)
        })
        tata_quotes.insert_one({
            "min_age":min_age,"max_age":max_age,"si":si,"premium":round(base*1.15,2)
        })

print("✅ Premiums inserted successfully")
