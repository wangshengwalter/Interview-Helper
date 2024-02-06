import yake

kw_extractor = yake.KeywordExtractor(lan="en", n=7, dedupLim=0.9, windowsSize=5, top=5)

txt0 = "What is Java? "
txt1 = "Why is Java a platform independent language?"
txt2 = "Why is Java not a pure object oriented language?"
txt3 = "What is the difference between C++ and Java?"
txt4 = "Difference between Heap and Stack Memory in java. And how java utilizes this."

for txt in [txt0, txt1, txt2, txt3, txt4]:
    keywords = kw_extractor.extract_keywords(txt)
    print(keywords)