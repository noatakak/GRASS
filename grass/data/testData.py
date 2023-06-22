import fandom
import pandas as pd
import json

def cleanList():
#   cleans up the copy and pasted list of items from GITM
    read_file = pd.read_csv("items.txt")
    df = []
    for i in range(65):
        listOfWordsNums = read_file.iloc[i][0].split()
        k = ""
        for x in listOfWordsNums:
            if (not isinstance(x, str)) or '.' in x:
                print(x)
                df.append(k)
                k = ""
            else:
                if k != "":
                    k += " "
                k += x
    return df

def buildJson(df):
    fandom.set_wiki("minecraft")
    jason = []
    for item in df:
        page = fandom.page(title=item)
        desc = page.summary
        # craft = getCraftData(df, item)
        # desc = desc + "Recipe Ingredients: " + craft[0]
        data = {
            "item" : item,
            "description" : desc
        }
        jason.append(data)
    return jason


def writeJason(jason):
    with open("item_desc.json", 'w') as file:
        json.dump(jason, file)
    print("JSON data has been written to item_desc.json")


def main():
    dataframe = cleanList()
    jason = buildJson(dataframe)
    writeJason(jason)


main()
