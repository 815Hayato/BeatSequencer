import re
import numpy as np
import wave
import struct
import pandas as pd
import pygame
import time
import threading
import os
import tkinter as tk
from tkinter import scrolledtext


###音声ファイル(音源)のデータを読み取る関数
def load(string):
    ##コマンドをloadコマンドの詳細な正規表現に照合する
    match = pLoad.match(string)
    if (match == None) or (match.group() != string): #照合失敗
        print("Invalid Syntax")
    else: #照合成功
        filename = match.group(1) #音源のwavファイルの名前
        soundname = match.group(2) #GUIでの使う際の名前
        if soundname in SoundArrayDictionary: #既に登録された音源の使用名だった場合
            print("SoundNameAlreadyExist")
        elif filename in SoundFileList: #既に登録された音源だった場合
            print("FileAlredyLoaded")
        else:
            ##音源のwavファイルを読み込む
            try:
                with wave.open("./Sounds/"+filename+".wav","rb") as f: #soundsフォルダから音源のwaveファイルを取り出す
                    SoundParams = f.getparams()
                    if (SoundParams[1]==2)and(SoundParams[2]==44100)and(SoundParams[0]==2): #音源のチャンネル数が2、サンプル幅が2、サンプリング周波数が44100であれば使用できる
                        Indata = f.readframes(-1) #音源のデータを取り出す
                        SoundArray = np.frombuffer(Indata,dtype="int16") #バイナリから数値に変換
                        SoundArrayDictionary[soundname] = SoundArray #音源の音声データを格納
                        SoundFileList.append(filename) #音源の使用名を格納
                        labeltext = soundname + ":   "+filename+".wav"
                        label = tk.Label(soundFrame,text=labeltext,bg="white",font=("メイリオ",10)) #GUIのlabel枠に表示
                        label.pack(anchor=tk.W)
                    else:
                        if SoundParams[0] != 2: #音源のチャンネル数が2でない場合
                            print("NChannelNot2: "+str(SoundParams[0]))
                        if SoundParams[1] != 2: #音源のサンプル幅が2でない場合
                            print("SampWidthNot2: "+str(SoundParams[1]))
                        if SoundParams[2] != 44100: #音源のサンプリング周波数が44100でない場合
                            print("FrameRateNot44100: "+str(SoundParams[2]))
            except FileNotFoundError: #ファイルが見つからない場合
                print("FileNotFound")



###
def extract(p,s,k=0,n=""):
    match = re.search(p,s)
    if match == None:
        return n
    else:
        return match.group(k)



###writeコマンドからリズム(譜面)を読み取る関数
def write(string):
    ##コマンドをwriteコマンドの詳細な正規表現に照合する
    match0 = pWrite.match(string)
    if (match0 == None) or (match0.group() != string): #照合失敗
        print("InvalidSyntax")
    else: #照合成功
        code = match0.group(1) #譜面(リズム)の詳細
        framename = match0.group(2) #譜面(リズム)の名前
        if framename in FrameDataDictionary: #既に登録された譜面名だった場合
            print("FrameNameAlreadyExist")
        else:
            match1 = pCode.match(code)
            if (match1 == None) or (match1.group() != code):
                print("CodeInvalidSyntax")
            else:
                ##譜面(リズム)表記から各音符の表記を取り出す
                eachRhythm = pRhythm.findall(code)
                n = 0
                for rhythm in eachRhythm: #各音符に対して正規表現と照合する
                    match2 = pDetail.match(rhythm)
                    if (match2 == None) or (match2.group() != rhythm): #照合失敗
                        print(rhythm + " CodeInvalidSyntax")
                        n += 1
                if n == 0: #全ての音符表記について照合成功
                    df = pd.DataFrame(np.zeros([0,4]),dtype=object)
                    df.columns = ["sound","addition","partframes","allframes"]
                    count = 0
                    afrs = 0
                    for (i,str0) in enumerate(eachRhythm):
                        snd = extract(p_sound,str0,1) #
                        add = extract(p_add,str0) 
                        btm = int(extract(p_bottom,str0)) 
                        top = int(extract(p_top,str0,1,1)) 
                        rep = int(extract(p_repeat,str0,1,1)) 
                        frs = int((basetime*top*88200)/btm) #88200 = 44100*2
                        for i in range(rep):
                            afrs += frs
                            df.loc[str(count)] = [snd,add,frs,afrs]
                            count += 1
                    if afrs > nframes: #surplusDelete
                        while df.iat[-1,3] > nframes:
                            df.drop(df.index[-1],inplace=True)
                            count -= 1
                        while df.iat[-1,3] < nframes:
                            snd = "0"
                            add = ""
                            frs = nframes - df.iat[-1,3]
                            print(frs)
                            afrs = df.iat[-1,3] + frs
                            df.loc[str(count)] = [snd,add,frs,afrs]
                    if afrs < nframes: #blankFill
                        snd = "0"
                        add = ""
                        frs = nframes - df.iat[-1,3]
                        afrs += frs
                        df.loc[str(count)] = [snd,add,frs,afrs]
                    FrameDataDictionary[framename] = df
                    labeltext = framename + ":  " + code
                    label = tk.Label(rhythmFrame,text=labeltext,bg="white",font=("メイリオ",10))
                    label.pack(anchor=tk.W)



def set(string):
    match = pSet.match(string)
    if (match == None)or(match.group() != string):
        print("Invalid Syntax")
    else:
        objectname = match.group(1)
        soundname = match.group(2)
        framename = match.group(3)
        if objectname in ObjectArrayDictionary:
            print("ObjectNameAlreadyExist")
        else:
            if (framename in FrameDataDictionary)and(soundname in SoundArrayDictionary):
                ObjectArray = np.array([],dtype="int64")
                sounddata = SoundArrayDictionary[soundname]
                framedata = FrameDataDictionary[framename]
                for i in framedata.index: 
                    sound = framedata.at[i,"sound"]
                    frs = framedata.at[i,"partframes"]
                    addmark = framedata.at[i,"addition"]
                    if addmark == "":
                        scale = 1
                    elif addmark == "^":
                        scale = 2.5
                    else:
                        scale = 0.5
                    if sound == "0":
                        blank = np.zeros(frs,dtype="int64")
                        ObjectArray =np.concatenate([ObjectArray,blank])
                    elif frs <= len(sounddata):
                        copy = sounddata[:frs] * scale
                        copy = copy.astype("int64")
                        ObjectArray = np.concatenate([ObjectArray,copy])
                    else:
                        blank = np.zeros(frs-len(sounddata),dtype="int64")
                        copy = sounddata * scale
                        copy = copy.astype("int64")
                        ObjectArray = np.concatenate([ObjectArray,copy,blank])
                ObjectArrayDictionary[objectname] = ObjectArray
                labeltext = objectname + ":  " + soundname + "+" + framename
                label = tk.Label(objectFrame,text=labeltext,bg="white",font=("メイリオ",10))
                objectLabels[objectname] = label
                label.pack(anchor=tk.W)
            else:
                if framename not in FrameDataDictionary:
                    print("FrameNotFound")
                if soundname not in SoundArrayDictionary:
                    print("SoundNotFound")



def addomit(string):
    if (string.count("add")>=2) or (string.count("omit")>=2):
        print("Invalid Syntax")
    else:
        if (string.count("add") == 1)and(string.count("omit")==0):
            add(string)
        elif (string.count("omit") == 1)and(string.count("add")==0):
            omit(string)
        else:
            if string.index("add") <= string.index("omit"):
                add(string)
                omit(string)
            else:
                print("Invalid Syntax")



def add(string):
    global change
    match = pAdd.search(string)
    if match != None:
        names = re.split(",",match.group(1))
        for name in names:
            if (name in ObjectArrayDictionary)and(name not in PlayingObjectList):
                PlayingObjectList.append(name)
                change = 1
                objectLabels[name].configure(font=("メイリオ",9,"bold"))
            else:
                if name not in ObjectArrayDictionary:
                    print(name+" :ObjectNotFound")
                if name in PlayingObjectList:
                    print(name+" :ObjectAlreadyPlaying")



def omit(string):
    global change
    match = pOmit.search(string)
    if match != None:
        names = re.split(",",match.group(1))
        for name in names:
            if (name in ObjectArrayDictionary)and(name in PlayingObjectList):
                PlayingObjectList.remove(name)
                objectLabels[name].configure(font=("メイリオ",10,"normal"),fg="black")
                change = 1
            else:
                if name not in ObjectArrayDictionary:
                    print(name+" :ObjectNotFound")
                if name not in PlayingObjectList:
                    print(name+" :ObjectNotPlaying")



def makesound(): 
    PlayingArray = np.zeros(nframes,dtype="int64")
    for objectname in PlayingObjectList:
        PlayingArray += ObjectArrayDictionary[objectname]
        objectLabels[objectname].configure(fg = "green")
    PlayingArray = np.clip(PlayingArray,-32767,32767) #32767 = 2**8/2 -1
    biArray = struct.pack("h"*len(PlayingArray),*PlayingArray)
    param = (2,2,44100,len(biArray),"NONE","not compressed")
    with wave.open(os.path.join(dirpath,"Phase"+str(phase+1)+".wav"),"wb") as f:
        f.setparams(param)
        f.writeframes(biArray)



###オーディオでwavファイルを再生する関数
def audio(): 
    while p == 1:
        pygame.mixer.music.load(dirpath+"/Phase"+str(phase)+".wav")
        pygame.mixer.music.play()
        time.sleep(entiretime)



###GUIの入力を読み取って各コマンドに仕分ける関数
def readCode(event):
    ##入力されたテキストの下処理(入力→各コマンドの配列)
    text = textField.get("1.0","end")
    textField.delete("1.0","end")
    lines1 = text.split("\n") #入力を改行ごとに分ける
    lines2 = []
    for line in lines1:
        if line != "": #行間は省く
            lines2.append(line)

    ##各コマンドを正規表現に照合する関数(checkCode)に送る
    if len(lines2) == 0: #コマンドが無い場合
        print("PleaseTypeCommands")
    elif len(lines2) == 1: #コマンドが1つの場合
        command = lines2[0]
        checkCode(command)
    else: #コマンドを複数記述する場合load,write,setコマンドしか記述できない
        for command in lines2:
            i = re.match("\S*",command) #コマンドの種類を判別
            v = i.group()
            if (v=="load")or(v=="write")or(v=="set"):
                checkCode(command)
            else:
                print("OnlyUseLoad,Write,Set")



###各コマンドを識別し、適切な処理を行う関数に送る関数
def checkCode(command):
    global p,change,phase #変数の詳細は366行を参照
    matchAll = pCommand.match(command) #存在するコマンドか確認(load,write,setなど)
    if matchAll == None: #存在しないコマンドの場合
        print("NoSuchCommand")
    else: #存在するコマンドの場合
        ##loadコマンドの場合、load関数へ
        if matchAll.group() == "load":
            load(command)

        ##writeコマンドの場合、write関数へ
        elif matchAll.group() == "write":
            write(command)

        ##setコマンドの場合、set関数へ
        elif matchAll.group() == "set":
            set(command)

        ##addコマンド、またはomitコマンドの場合、addomit関数へ
        elif (matchAll.group() == "add") or (matchAll.group() == "omit"):
            addomit(command)
            if (PlayingObjectList == [])and(p == 1): #再生してよいオブジェクトがなくなった場合はオーディオを停止
                print("AutomaticallyHalted")
                p = 0
            if (p == 1)and(change == 1): #オーディオが再生状態なら新しくwavファイルを作って変更を反映、再生状態でないならそのまま
                makesound()
                phase += 1
                change = 0

        ##playコマンドの場合、play関数へ
        elif matchAll.group() == "play":
            if p == 1:
                print("AlreadyPlaying")
            else: #PlayingArrayが空でも再生可。
                if change == 1:
                    makesound()
                    phase += 1
                    change = 0
                if change == 0:
                    for objectname in PlayingObjectList:
                        objectLabels[objectname].configure(fg = "green")
                p = 1
                audiothread = threading.Thread(target = audio)
                audiothread.start()

        ##haltコマンドの場合、halt関数へ
        elif matchAll.group() == "halt":
            if p == 0:
                print("AlreadyHalted")
            else:
                p = 0
                for name in PlayingObjectList:
                    objectLabels[name].configure(fg="black")
        
        ##quitコマンドの場合、quit関数へ
        elif matchAll.group() == "quit":
            if p == 1: #オーディオが再生状態の場合
                print("SoundStillPlaying") #先にhaltコマンドでオーディオを止めるようメッセージを送る
            else: #オーディオが停止状態の場合
                print("GoodBye")
                root.destroy()



###正規表現の確認(入力されたコードを照合するの際に使用)
pCommand = re.compile(r"load|write|set|add|omit|play|halt|quit")
pMeasure = re.compile(r"/([1-9]\d*):([1-9]\d*)@([1-9]\d*)\s*") #拍子+テンポ表記の正規表現
pLoad = re.compile(r"load\s+(\w+)\s+as\s+(\w+)\s*")
pWrite = re.compile(r"write\s+(\S+)\s+as\s+(\w+)\s*")
pSet = re.compile(r"set\s+(\w+)\s+by\s+(\w+),(\w+)\s*")
pAdd = re.compile(r"add\s+(\w+(,\w+)*)+\s*")
pOmit = re.compile(r"omit\s+(\w+(,\w+)*)+\s*")
pCode = re.compile(r"(/[^/]+)+")
pRhythm = re.compile(r"/[^/]+")
pDetail = re.compile(r"/0?[\^-]?[1-9]\d*(:[1-9]\d*)?(;[1-9]\d*)?")
p_sound = "/(0?)" 
p_add = "[\^-]"
p_bottom = "\d+"
p_top = ":(\d+)"
p_repeat = ";(\d+)"



###音声データと各変数の辞書
SoundArrayDictionary = {} #使用する音源の音声データを格納
SoundFileList = [] #音源の使用名を格納
FrameDataDictionary = {}
ObjectArrayDictionary = {}
PlayingObjectList = []
soundLabels = {}
rhythmLabels = {}
objectLabels = {}



###音声再生を担うモジュールの初期設定
pygame.mixer.init(frequency = 44100)
p = 0 #0ならオーディオは休止状態、1なら再生状態
phase = 0 #(再生する音楽の)変更回数をカウント
change = 0 #再生されている音楽に変更を加える必要が生じているか(0なら必要なし、1なら必要あり)



###コマンドプロンプト上で行う操作(プロジェクト名・テンポ・拍子の設定)
##プロジェクト名の設定
ProjectName = input("project--> ") #プロジェクト名の入力を要求
print("ProjectName:"+ProjectName)
dirpath = "./"+ProjectName+"_music"
os.makedirs(dirpath, exist_ok = True) #対応するフォルダを作成
print()

##テンポと拍子の設定
while True:
    measure = input("measure--> ") #テンポと拍子の設定を要求する
    match0 = pMeasure.match(measure) #正規表現と入力の照合
    #照合失敗
    if (match0 == None) or (match0.group() != measure):
        print("Invalid Syntax")
    #照合成功
    else:
        measure_bottom = int(match0.group(1))
        measure_top = int(match0.group(2))
        tempo = int(match0.group(3))
        basetime = 60/tempo #一拍の長さ[秒]
        entiretime = basetime * measure_top / measure_bottom #一小節の長さ[秒]
        nframes = int(88200*entiretime) #一小節のフレーム数 88200=44100(サンプル周波数)*2(sampWidth)
        break
print("Now,ThisWindowWillShowErrorMessageWhenNecessary.")



###GUIの立ち上げ(tkinterを使用)
##初期設定
root = tk.Tk()
root.geometry("960x600")
root.configure(bg="white")
root.title("Rhythm Programming") #GUIのタイトル名

##ラベル・枠の記述
ProjectLabel = tk.Label(root,text=ProjectName,bg="white",font=("",24,"bold"))
MeasureLabel = tk.Label(root,text=measure,bg="white",font=("",24,"bold"))
soundFrame = tk.LabelFrame(root,text="sound",bg="white",font=("",16,"bold"))
rhythmFrame = tk.LabelFrame(root,text="rhythm",bg="white",font=("",16,"bold"))
objectFrame = tk.LabelFrame(root,text="object",bg="white",font=("",16,"bold"))
textFrame = tk.LabelFrame(root,text="command",bg="white",font=("",16,"bold"))
textField = scrolledtext.ScrolledText(textFrame,blockcursor=True,font=("メイリオ",10),height=5)

##配置の記述1(スペースのグリッドを記述)
root.grid_columnconfigure(0,weight=1)
root.grid_columnconfigure(1,weight=1)
root.grid_rowconfigure(1,weight=1)
root.grid_rowconfigure(2,weight=1)

##配置の記述2(ラベル・枠の配置)
ProjectLabel.grid(row=0,column=0)
MeasureLabel.grid(row=0,column=1)
soundFrame.grid(row=1,column=0,sticky=tk.NSEW) #使用できる音源(wavファイル)を表示する枠
rhythmFrame.grid(row=2,column=0,sticky=tk.NSEW) #適用できるリズム(=楽譜)を表示する枠
objectFrame.grid(row=1,column=1,rowspan=2,sticky=tk.NSEW) #音源とリズムの組(object)を表示する枠
textFrame.grid(row=3,column=0,columnspan=2,sticky=tk.NSEW) #コマンドを入力する枠
textField.pack(fill=tk.BOTH)
textField.bind("<Shift-Return>",readCode) #shift+改行で入力テキストを読み取って関数

##GUIを動かす
root.mainloop()


###終了時にデータを初期化
SoundArrayDictionary = {}
SoundFileList = []
FrameDataDictionary = {}
ObjectArrayDictionary = {}
PlayingObjectList = []
PlayingArray = []
p = 0
phase = 0
change = 0
soundLabels = {}
rhythmLabels = {}
objectLabels = {}
