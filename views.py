from django.shortcuts import render
from django.template import RequestContext
from django.contrib import messages
import pymysql
from django.http import HttpResponse
import json
from string import punctuation
from nltk.corpus import stopwords
import nltk
from nltk import tokenize
from heapq import nlargest
from rouge_score import rouge_scorer
import matplotlib.pyplot as plt
from transformers import pipeline
import pandas as pd
import io
import base64

global uname
stop_words = set(stopwords.words('english'))

#function to summarize essay
def summarize(essay, threshold):
    word_frequencies = {}
    tokens = essay.split(" ")
    for word in tokens:
        if word.lower() not in stop_words:
            if word not in word_frequencies.keys():
                word_frequencies[word] = 1
            else:
                word_frequencies[word] += 1
    max_frequency = max(word_frequencies.values())
    for word in word_frequencies.keys():
        word_frequencies[word] = word_frequencies[word]/max_frequency
    sentence_tokens = tokenize.sent_tokenize(essay) 
    sentence_scores = {}
    for sent in sentence_tokens:
        words = sent.split(" ")
        for word in words:
            if word.lower() in word_frequencies.keys():
                if sent not in sentence_scores.keys():
                    sentence_scores[sent] = word_frequencies[word.lower()]
                else:
                    sentence_scores[sent] += word_frequencies[word.lower()]  
    select_length = int(len(sentence_tokens)*threshold)
    summary = nlargest(select_length, sentence_scores, key = sentence_scores.get)
    final_summary = [word for word in summary]
    summary = ' '.join(final_summary)  
    return summary

file = open('Dataset/tldrlegal_v1.json')
data = json.load(file)
file.close()
scorer = rouge_scorer.RougeScorer(['rouge1', 'rougeL'], use_stemmer=True) #calculate rouge scrore between test and predicted

precision = 0
recall = 0
fscore = 0
pre = []
rec = []
fsc = []
j = 0
original_data = None
original_sum = None
for key, value in data.items():
    text = value['original_text']
    summary = value['reference_summary']
    if j == 2:
        original_data = text
        original_sum = summary
    nlp_summary = summarize(text, 0.95)
    scores = scorer.score(summary, nlp_summary)
    score = scores['rouge1']
    #print(score)
    p = score[0]
    r = score[1]
    f = score[2]
    if p > precision:
        precision = p
    if r > recall:    
        recall = r
    if f > fscore:    
        fscore = f
    j += 1    
pre.append(precision)
rec.append(recall)
fsc.append(fscore)
transformer = pipeline("summarization")
predict = transformer(original_data)[0]['summary_text']
scores = scorer.score(original_sum, predict)
score = scores['rouge1']
p = score[0]
r = score[1]
f = score[2]
pre.append(p)
rec.append(r)
fsc.append(f)

def TrainNLP(request):
    if request.method == 'GET':
        global precision, recall, fscore
        output = ''
        output+='<table border=1 align=center width=100%><tr><th><font size="" color="black">Algorithm Name</th><th><font size="" color="black">Precision</th>'
        output+='<th><font size="" color="black">Recall</th><th><font size="" color="black">FMEASURE</th></tr>'
        algorithms = ['NLP Summary', 'Transformer Summary']
        output+='<tr><td><font size="" color="black">'+algorithms[0]+'</td><td><font size="" color="black">'+str(pre[0])+'</td><td><font size="" color="black">'+str(rec[0])+'</td><td><font size="" color="black">'+str(fsc[0])+'</td></tr>'
        output+='<tr><td><font size="" color="black">'+algorithms[1]+'</td><td><font size="" color="black">'+str(pre[1])+'</td><td><font size="" color="black">'+str(rec[1])+'</td><td><font size="" color="black">'+str(fsc[1])+'</td></tr>'
        output+= "</table></br></br>"
        df = pd.DataFrame([['NLP Summary','Precision',pre[0]],['NLP Summary','Recall',rec[0]],['NLP Summary','F1 Score',fsc[0]],
                           ['Transformer Summary','Precision',pre[1]],['Transformer Summary','Recall',rec[1]],['Transformer Summary','F1 Score',fsc[1]],                           
                          ],columns=['Algorithms','Metrics','Value'])
        df.pivot_table(index="Algorithms", columns="Metrics", values="Value").plot(kind='bar', figsize=(5, 3))
        plt.title("All Algorithms Performance Graph")
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        img_b64 = base64.b64encode(buf.getvalue()).decode()    
        context= {'data':output, 'img': img_b64}
        return render(request, 'UserScreen.html', context)         

def UserLogin(request):
    if request.method == 'GET':
       return render(request, 'UserLogin.html', {})

def index(request):
    if request.method == 'GET':
       return render(request, 'index.html', {})

def Signup(request):
    if request.method == 'GET':
       return render(request, 'Signup.html', {})

def Aboutus(request):
    if request.method == 'GET':
       return render(request, 'Aboutus.html', {})

def SignupAction(request):
    if request.method == 'POST':
        username = request.POST.get('t1', False)
        password = request.POST.get('t2', False)
        contact = request.POST.get('t3', False)
        email = request.POST.get('t4', False)
        address = request.POST.get('t5', False)
        
        status = 'none'
        con = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'summary',charset='utf8')
        with con:
            cur = con.cursor()
            cur.execute("select username from signup where username = '"+username+"'")
            rows = cur.fetchall()
            for row in rows:
                if row[0] == email:
                    status = 'Given Username already exists'
                    break
        if status == 'none':
            db_connection = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'summary',charset='utf8')
            db_cursor = db_connection.cursor()
            student_sql_query = "INSERT INTO signup(username,password,contact_no,email_id,address) VALUES('"+username+"','"+password+"','"+contact+"','"+email+"','"+address+"')"
            db_cursor.execute(student_sql_query)
            db_connection.commit()
            print(db_cursor.rowcount, "Record Inserted")
            if db_cursor.rowcount == 1:
                status = 'Signup Process Completed'
        context= {'data':status}
        return render(request, 'Signup.html', context)

def UserLoginAction(request):
    if request.method == 'POST':
        global uname
        option = 0
        username = request.POST.get('username', False)
        password = request.POST.get('password', False)
        con = pymysql.connect(host='127.0.0.1',port = 3306,user = 'root', password = 'root', database = 'summary',charset='utf8')
        with con:
            cur = con.cursor()
            cur.execute("select * FROM signup")
            rows = cur.fetchall()
            for row in rows:
                if row[0] == username and row[1] == password:
                    uname = username
                    option = 1
                    break
        if option == 1:
            output = "Welcome "+uname
            context= {'data':output}
            return render(request, 'UserScreen.html', context)
        else:
            context= {'data':'Invalid login details'}
            return render(request, 'UserLogin.html', context)

def GenerateSummary(request):
    if request.method == 'GET':
        return render(request, 'GenerateSummary.html', {})

def GenerateSummaryAction(request):
    if request.method == 'POST':
        global uname
        textdata = request.POST.get('t1', False)
        summary = summarize(textdata, 0.3)
        '''
        output = '<table align="center" width="80">'
        output += '<tr><td><font size="3" color="black">Input&nbsp;Text</b></td><td><textarea name="t1" rows="15" cols="80">'+textdata+'</textarea></td></tr>'
        output += '<br/><br/><tr><td><font size="3" color="black">Generated&nbsp;Summary</b></td><td><textarea name="t2" rows="10" cols="80">'+summary+'</textarea></td></tr>'
        output += "</table></br></br></br>"
        '''

        output = '<p align="justify"><font size="3" style="font-family: Comic Sans MS" color="black">Input Text = '+textdata+'</p><br/>'
        output += '<p align="justify"><font size="3" style="font-family: Comic Sans MS" color="black">Generated Summary = '+summary+'</p><br/><br/><br/><br/><br/>'
        context= {'data':output}
        return render(request, 'UserScreen.html', context)
















        

