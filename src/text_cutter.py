import os

def documentation_iteration():
    dir_path = "./NetworkProtocols"
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)
        f = open(file_path, "r")
        #for every file you scraped, filter it using splitters
        splitter(f, filename)

def splitter(file, filenamefull):

    dir_path = "./SplitDocumentation"

    if not os.path.exists(dir_path):
        os.mkdir(dir_path)

    #the name of the file besides the .txt
    filename = filenamefull[:-4]
    #get the content of the file
    content = file.read()
    #make the file in SplitDocumentation
    f = open(f"./SplitDocumentation/{filename}.txt", "a+")
    
    #store each paragraph in here, and each paragraph will be written to the split file
    paragraphs = []
    paragraph = ""

    #Here is where we actually start filtering, going character by character
    for i in range(len(content) - 1):
        if (i < len(content) - 2):
            #only include alphanumerical and spaces in this new file
            if (content[i + 1] != '\n' and content[i + 2] != '\n' and (content[i].isalnum() or content[i] == " ")):
                paragraph = paragraph + content[i]
            else:
                paragraphs.append(paragraph)
                paragraph = ""

    for para in paragraphs:
        if len(para) < 30: #probably not significant information. probably just a header or something
            paragraphs.remove(para)
        else:        
            para.strip()

    #write each paragraph in the file to this new filtered file
    for para in paragraphs:
        f.write(para)