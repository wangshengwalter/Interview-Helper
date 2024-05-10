# This Python file uses the following encoding: utf-8
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSettings, pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QHBoxLayout
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QStackedWidget
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QGroupBox
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtWidgets import QScrollArea
from PyQt5.QtWidgets import QSizePolicy

from PyQt5.QtWidgets import QWidget

from backimgw import BackImgW

import pyaudiowpatch as pyaudio
from google.cloud import speech
from openai import OpenAI

import queue
import threading
import os
import asyncio
import csv
import spacy
import re

spacy_nlp = spacy.load("zh_core_web_sm")

loop = asyncio.get_event_loop()

RATE = 16000
CHUNK = int(RATE / 10)  # 100ms
DeviceIndexPick = None
openai_apikey = ""


class MainWindow(QMainWindow):

    mainstackw = None

    # widget 1
    # 1.1
    DevicePickCombox = None
    DeviceIndexList = []
    DeviceRateList = []
    DeviceNamePick = None

    # 1.2
    Areas = []
    ChoosenAreas = []
    AreaCheckBoxes = []

    # 1.3
    # None

    # 1.4
    api_linedit = None

    widget1_nextbtn = None

    # widget 2
    recongtxttitle = "Speech to Text Result:"
    recongtxt = ""
    recongtxtlabel = None
    keywords = []
    keywordbtns = []

    audioControlbtn = None
    recog_thread = None
    audioon = False
    audioon_lock = None
    MicStreaming = None

    chatgptshow_thread = None
    chatgptshow_status = False
    chatgptshow_status_lock = None
    ai_ans_label = None
    ai_ans = "Chatgpt answer:"

    PreparedQuestion = []
    SearchedQ_thread = None
    SearchedQ_status = False
    SearchedQ_status_lock = None
    Searched_result_showingwidget = None
    testlayout = None
    signal_cleanquestionlist = pyqtSignal()
    signal_addquestion = pyqtSignal(int)
    pre_ans_label = None
    pre_ans = "Prepared answer"

    def refreshdevice(self):
        self.DevicePickCombox.clear()
        self.DeviceIndexList.clear()
        self.DeviceRateList.clear()

        p = pyaudio.PyAudio()
        deviceinfo = p.get_loopback_device_info_generator()
        for loopback in deviceinfo:
            self.DevicePickCombox.addItem(loopback["name"])
            self.DeviceIndexList.append(loopback["index"])
            self.DeviceRateList.append(int(loopback["defaultSampleRate"]))
#            print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
#            print(loopback["index"])
#            print(loopback["name"])
        p.terminate()

        print(self.DeviceIndexList)
        print(self.DeviceRateList)

        self.pickaudiodevice()

    def pickaudiodevice(self):
        if len(self.DeviceIndexList) != 0:
            DeviceNamePick = self.DevicePickCombox.currentText()
            global DeviceIndexPick
            DeviceIndexPick = self.DeviceIndexList[self.DevicePickCombox.currentIndex()]
            global RATE
            RATE = self.DeviceRateList[self.DevicePickCombox.currentIndex()]

            if DeviceNamePick == "" or DeviceIndexPick is None:
                self.widget1_nextbtn.setEnabled(False)
            else:
                self.widget1_nextbtn.setEnabled(True)
                print("pick device: " + DeviceNamePick)
                print("pick device index: ", DeviceIndexPick)

    def pickareas(self):
#        print("areas changes")
        self.ChoosenAreas.clear()

        for checkbox in self.AreaCheckBoxes:
            if checkbox.isChecked():
                self.ChoosenAreas.append(checkbox.text())

#        print(self.ChoosenAreas)
#        if len(self.ChoosenAreas) <= 0:
#            self.nextbtn_2.setEnabled(False)
#        else:
#            self.nextbtn_2.setEnabled(True)

    def sava_OpenAI_key(self):
        key = self.api_linedit.text()

        setting_file = QSettings('Interview Helper', 'Key')
        setting_file.setValue('ChatGPT_API_Key', key)

    def load_OpenAI_key(self):
        setting_file = QSettings('Interview Helper', 'Key')
        key = setting_file.value('ChatGPT_API_Key', type=str)

        if key is not None and key != "0":
            self.api_linedit.setText(key)
            self.api_linedit.home(True)
        else:
            self.api_linedit.clear()

    def Go_Interview(self):
        global openai_apikey
        openai_apikey = self.api_linedit.text()
        self.sava_OpenAI_key()

        #load prepared question
        # 预载文件
        print("start read csv")
        for filename in self.ChoosenAreas:
            filepath = "res\\"+filename+".csv"
            with open(filepath, 'r', encoding='utf-8') as csvfile:
                data_onefile = list(csv.reader(csvfile))
                self.PreparedQuestion.extend(data_onefile)
        print("finish read csv")


        self.mainstackw.setCurrentIndex(1)

    def control_speechtotext(self):
        if self.audioon:
            print("finisn speech to text")
            # send question to chatgpt as sonn as possible
            if self.ai_ans_label is not None:
                self.chatgptshow_status_lock.acquire()
                self.chatgptshow_status = True
                self.chatgptshow_status_lock.release()
                self.chatgptshow_thread = threading.Thread(target=MainWindow.ask_openai, args=(self,))
                self.chatgptshow_thread.start()
            # start find the prepared question
            if self.pre_ans_label is not None:
                self.SearchedQ_status_lock.acquire()
                self.SearchedQ_status = True
                self.SearchedQ_status_lock.release()
                self.SearchedQ_thread = threading.Thread(target=MainWindow.SearchPreparedQuestion, args=(self,))
                self.SearchedQ_thread.start()

            # end the speech to text
            self.audioon_lock.acquire()
            self.audioon = False
            self.audioon_lock.release()
            if self.MicStreaming is not None:
                self.MicStreaming.finish()
            if self.recog_thread is not None:
                self.recog_thread.join()

            # refresh the QPushbutton status
            self.audioControlbtn.setStyleSheet("background-color : white")
            self.audioControlbtn.setText("Start")

        else:
            print("start speech to text")
            # don update chatgpt ans now! start next task
            self.chatgptshow_status_lock.acquire()
            self.chatgptshow_status = False
            self.chatgptshow_status_lock.release()
            # don finding prepared ans! start next task
            self.SearchedQ_status_lock.acquire()
            self.SearchedQ_status = False
            self.SearchedQ_status_lock.release()
            # wait chatgpt and localAnsSearch done
            if self.chatgptshow_thread is not None:
                self.chatgptshow_thread.join()
            if self.SearchedQ_thread is not None:
                self.SearchedQ_thread.join()

            # Refresh variable
            self.recongtxt = ""
            # start speech to text
            self.audioon_lock.acquire()
            self.audioon = True
            self.audioon_lock.release()
            self.recog_thread = threading.Thread(target=MainWindow.recog, args=(self,))
            self.recog_thread.start()
            # Refresh UI
            self.audioControlbtn.setStyleSheet("background-color : red")
            self.audioControlbtn.setText("Finish")

    def refresh_recotext(self, responses: object) -> None:
        for response in responses:
            if not self.audioon:
                break
            if not response.results:
                continue

            result = response.results[0]

            if not result.alternatives:
                continue

            transcript = result.alternatives[0].transcript or ""
            if not result.is_final:
                self.recongtxtlabel.setText(self.recongtxt+"\n"+transcript)
#                print("not final:  " + self.recongtxt+"\n"+transcript)
            else:
                self.recongtxt = self.recongtxt + "\n" + transcript
                self.recongtxtlabel.setText(self.recongtxt)

    def recog(self) -> None:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "res\google_key.json"
        language_code = "cmn-Hans-CN"  # a BCP-47 language tag   cmn-CN  en-US  cmn-Hans-CN

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=RATE,
            language_code=language_code,
            enable_automatic_punctuation=True,
        )

        streaming_config = speech.StreamingRecognitionConfig(
            config=config, interim_results=True
        )

        client = speech.SpeechClient()

        global DeviceIndexPick
#        print(DeviceIndexPick)
        if DeviceIndexPick is not None:
            print(int(RATE / 10))
            with MicrophoneStream(RATE, int(RATE / 10)) as stream:
                self.MicStreaming = stream
                audio_generator = stream.generator()
                requests = (
                    speech.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator
                )

                responses = client.streaming_recognize(streaming_config, requests)
                self.refresh_recotext(responses)

    def ask_openai(self):
        self.ai_ans = ""
        client = OpenAI(
            api_key=openai_apikey
        )
        # uncomment here to change to english
#        questionHead = "Please answer in Chinese and then in English: "
        questionHead1 = "请解释一下"
        # TODO
        mode = False
        question = None
        # 如果语音很短，google只会给出识别标识为不确定，导致label里面的内容是最新的，但记录值由于只记录确定的识别内容，所以还没有更新。
        if mode is True:
            question = questionHead1+self.recongtxt
        else:
            question = questionHead1+self.recongtxtlabel.text()

#        print("语音识别展示内容：", self.recongtxtlabel.text())
        print("Chatgpt提问：", question)
        stream = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": question,
                }
            ],
            model="gpt-3.5-turbo",
            max_tokens=1000,
            stream=True
        )
        for chunk in stream:
            if self.chatgptshow_status is False:
                print("ans is cut off")
                return
            self.ai_ans = self.ai_ans + (chunk.choices[0].delta.content or "")
            self.ai_ans_label.setText(self.ai_ans)

    def SearchPreparedQuestion(self):
        FirstSearchQ = False
        Num_SearchedResult = 0
        if self.PreparedQuestion is not None:
            self.signal_cleanquestionlist.emit()
            print(self.Searched_result_showingwidget.width())

            # 将内容变成关键词
            keywords = spacy_nlp(self.recongtxtlabel.text()).ents
            print("keyword: ", keywords)
            # 根据关键词生成正则表达式
            pattern = re.compile('|'.join(re.escape(str(keyword)) for keyword in keywords), re.IGNORECASE)
            # 搜索相匹配的关键词
            for i in range(len(self.PreparedQuestion)):
                # interrupt searching local question
                if self.SearchedQ_status is False:
                    print("Interrupt Searching Local Prepared Questions")
                    break

                item = self.PreparedQuestion[i]
                if item[0] == "":
                    print("empty row: ", i)
                else:
                    if re.search(pattern, str(item[0])):
                        # 显示第一个匹配问题的答案
                        if FirstSearchQ is False:
                            FirstSearchQ = True
                            self.ShowPreparedAns(i)
                        self.signal_addquestion.emit(i)
                        Num_SearchedResult += 1
            self.Searched_result_showingwidget.setMinimumHeight(Num_SearchedResult*110)

    def clean_previous_searched_Question(self):
        # 将之前的内容全部删除，刷新UI
        while self.testlayout.count():
            btn = self.testlayout.takeAt(0).widget()
            if btn is not None:
                btn.deleteLater()

    def Add_Searched_Question(self, index):
        # 缩略展示所有相关的问题
        btn = QPushButton()
        btn.setText(str(self.PreparedQuestion[index][0]))
        btn.setMinimumHeight(100)
        self.testlayout.addWidget(btn)
        # 给所有问题添加槽函数
        btn.clicked.connect(lambda checked=None, index=index: self.ShowPreparedAns(index))

    def ShowPreparedAns(self, index):
        print(index)
        self.pre_ans_label.setText(str(self.PreparedQuestion[index][1]))

    def __init__(self):
        QMainWindow.__init__(self)
        self.setWindowTitle("InterView Helper")
        self.setWindowIcon(QIcon("res/interview.ico"))

        self.mainstackw = QStackedWidget()
        self.setCentralWidget(self.mainstackw)

        settingw = BackImgW()
        settingw.setbackimg("res/back1.png")
        self.mainstackw.addWidget(settingw)

        Helperw = BackImgW()
        Helperw.setbackimg("res/back2.png")
        Helperw.setMinimumSize(1300, 800)
        self.mainstackw.addWidget(Helperw)

        #1 widget  for sett audio device and area u want to choose, five tutorial and chatgpt api editor
        settingl = QHBoxLayout()
        settingl.setSpacing(20)
        settingl.setContentsMargins(40, 40, 40, 40) # left, top, right, bottom
        settingw.setLayout(settingl)

        # -----------------------------------------------------------
        device_area_l = QVBoxLayout()
        settingl.addLayout(device_area_l, 2)

        AudioDeviceChoosew = QGroupBox("Audio Device Selection")
        device_area_l.addWidget(AudioDeviceChoosew, 3)

        AreaChoosew = QGroupBox("Knowledge Domain Selection")
        device_area_l.addWidget(AreaChoosew, 7)

        # -----------------------------------------------------------
        info_api_l = QVBoxLayout()
        settingl.addLayout(info_api_l, 6)

        tutorialw = QGroupBox("Instruction")
        info_api_l.addWidget(tutorialw, 5)

        chatgptapiw = QGroupBox("Enter your ChatGpt APi: ")
        info_api_l.addWidget(chatgptapiw, 1)

        self.widget1_nextbtn = QPushButton("Next")
        info_api_l.addWidget(self.widget1_nextbtn, 1)
        self.widget1_nextbtn.setMinimumHeight(90)
        self.widget1_nextbtn.clicked.connect(lambda: self.Go_Interview())



        # 1.1 audio device choose
        AudioDeviceChoosel = QVBoxLayout()
#        AudioDeviceChoosel.setSpacing(20)
        AudioDeviceChoosew.setLayout(AudioDeviceChoosel)

        AudioDeviceChoosel.addSpacing(30)

        self.DevicePickCombox = QComboBox()
        AudioDeviceChoosel.addWidget(self.DevicePickCombox)
        self.DevicePickCombox.currentTextChanged.connect(lambda text: self.pickaudiodevice())

        refreshdevicebtn = QPushButton("Device Refresh")
        AudioDeviceChoosel.addWidget(refreshdevicebtn)
        refreshdevicebtn.clicked.connect(self.refreshdevice)

        self.refreshdevice()


        # 1.2 area choose
        AreaChoosel = QVBoxLayout()
        AreaChoosew.setLayout(AreaChoosel)


        for filename in os.listdir("res"):
            # Check if the file is a CSV file
            if filename.endswith(".csv"):
                # Strip the ".csv" extension and append the filename to the list
                self.Areas.append(filename[:-4])

        for area in self.Areas:
            areacheckbox = QCheckBox(area)
            AreaChoosel.addWidget(areacheckbox)
            areacheckbox.clicked.connect(lambda: self.pickareas())
            self.AreaCheckBoxes.append(areacheckbox)

        self.pickareas()


        # 1.3 tutorial
        infol = QVBoxLayout()
        tutorialw.setLayout(infol)

        infol.addSpacing(30)

        info_textedit = QTextEdit()
        with open("res\instru.txt", 'r') as file:
            content = file.read()
            info_textedit.setText(content)
        info_textedit.setReadOnly(True)
        infol.addWidget(info_textedit)


        # 1.4 openapi
        apil = QVBoxLayout()
        chatgptapiw.setLayout(apil)

        apil.addSpacing(30)

        self.api_linedit = QLineEdit()
        self.api_linedit.setPlaceholderText("Enter API here")
        apil.addWidget(self.api_linedit)

        self.load_OpenAI_key()


        # 2 widget
        interviewhelperl = QVBoxLayout()
        Helperw.setLayout(interviewhelperl)

        resultl = QHBoxLayout()
        interviewhelperl.addLayout(resultl)
        speechtotextl = QHBoxLayout()
        interviewhelperl.addLayout(speechtotextl)

        # ------------------------------------------
        SpeechtoTextbox = QGroupBox("Speech to Text: ")
        speechtotextl.addWidget(SpeechtoTextbox)
        SpeechtoTextLayout = QVBoxLayout()
        SpeechtoTextbox.setLayout(SpeechtoTextLayout)

        self.recongtxtlabel = QLabel("Google speech to txt result")
        # for test
#        self.recongtxtlabel = QLabel("Qt绑定信号槽有几种方式")

        self.recongtxtlabel.setWordWrap(True)
        SpeechtoTextLayout.addSpacing(30)
        SpeechtoTextLayout.addWidget(self.recongtxtlabel)
        # ------------------------------------------
        self.audioControlbtn = QPushButton("Start")
        self.audioControlbtn.setMinimumHeight(90)
        self.audioControlbtn.setMaximumWidth(400)
        self.audioControlbtn.setStyleSheet("background-color : white")
        self.audioControlbtn.clicked.connect(lambda: self.control_speechtotext())
        self.audioon_lock = threading.Lock()
        self.audioon_lock.acquire()
        self.audioon = False
        self.audioon_lock.release()
        speechtotextl.addWidget(self.audioControlbtn)


        LinkedQuestionBox = QGroupBox("Interview Question Found: ")
        resultl.addWidget(LinkedQuestionBox, 1)
        # ----------------------------------------------
        LinkedQuestionBoxl = QVBoxLayout()
        LinkedQuestionBox.setLayout(LinkedQuestionBoxl)
        LinkedQuestionBoxl.addSpacing(30)
        Searched_result_scrollarea = QScrollArea()
        Searched_result_scrollarea.setWidgetResizable(True);
        LinkedQuestionBoxl.addWidget(Searched_result_scrollarea)

        self.Searched_result_showingwidget = QWidget()
        self.Searched_result_showingwidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.Searched_result_showingwidget.setMinimumWidth(Searched_result_scrollarea.width())
        self.Searched_result_showingwidget.setMaximumHeight(0)
        Searched_result_scrollarea.setWidget(self.Searched_result_showingwidget)
        self.testlayout = QVBoxLayout()
        self.Searched_result_showingwidget.setLayout(self.testlayout)
        # 绑定槽函数和信号用来更新ui
#        signal_cleanquestionlist = QtCore.pyqtSignal()
#        signal_addquestion = QtCore.pyqtSignal(index)
        self.signal_cleanquestionlist.connect(self.clean_previous_searched_Question)
        self.signal_addquestion.connect(self.Add_Searched_Question)



        ShowAnswersl = QVBoxLayout()
        resultl.addLayout(ShowAnswersl, 1)
        # -----------------------------------------------
        ChatgptAnsBox = QGroupBox("Answer From ChatGPT: ")
        ShowAnswersl.addWidget(ChatgptAnsBox)

        ChatgptAnslayout = QVBoxLayout()
        ChatgptAnsBox.setLayout(ChatgptAnslayout)

        self.ai_ans_label = QLabel(self.ai_ans)
        self.ai_ans_label.setWordWrap(True)
        ChatgptAnslayout.addSpacing(30)
        ChatgptAnslayout.addWidget(self.ai_ans_label)

        self.chatgptshow_status_lock = threading.Lock()
        self.chatgptshow_status_lock.acquire()
        self.chatgptshow_status = False
        self.chatgptshow_status_lock.release()
        # -----------------------------------------------
        PreAnsBox = QGroupBox("Prepared Question: ")
        ShowAnswersl.addWidget(PreAnsBox)

        PreAnsLayout = QVBoxLayout()
        PreAnsBox.setLayout(PreAnsLayout)

        self.pre_ans_label = QLabel(self.pre_ans)
        self.pre_ans_label.setWordWrap(True)
        PreAnsLayout.addSpacing(30)
        PreAnsLayout.addWidget(self.pre_ans_label)

        self.SearchedQ_status_lock = threading.Lock()
        self.SearchedQ_status_lock.acquire()
        self.SearchedQ_status = False
        self.SearchedQ_status_lock.release()


class MicrophoneStream:
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(self: object, rate: int = RATE, chunk: int = int(RATE / 10)) -> None:
        self._rate = rate
        self._chunk = chunk

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self: object) -> object:
        self._audio_interface = pyaudio.PyAudio()

        global DeviceIndexPick

        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            # The API currently only supports 1-channel (mono) audio
            channels=1,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
            input_device_index=DeviceIndexPick,
        )

        self.closed = False

        return self

    def __exit__(
        self: object,
        type: object,
        value: object,
        traceback: object,
    ) -> None:
        """Closes the stream, regardless of whether the connection was lost or not."""
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def finish(self:object) -> None:
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(
        self: object,
        in_data: object,
        frame_count: int,
        time_info: object,
        status_flags: object,
    ) -> object:
        """Continuously collect data from the audio stream, into the buffer.

        Args:
            in_data: The audio data as a bytes object
            frame_count: The number of frames captured
            time_info: The time information
            status_flags: The status flags

        Returns:
            The audio data as a bytes object
        """
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self: object) -> object:
        """Generates audio chunks from the stream of audio data in chunks.

        Args:
            self: The MicrophoneStream object

        Returns:
            A generator that outputs audio chunks.
        """
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b"".join(data)


if __name__ == "__main__":
    app = QApplication([])

    styleFile = open("res/ui.qss", encoding="utf8")
    with styleFile:
        qss = styleFile.read()
        app.setStyleSheet(qss)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
