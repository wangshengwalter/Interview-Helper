# This Python file uses the following encoding: utf-8
import sys
from PySide2.QtWidgets import QApplication, QMainWindow
from PySide2.QtGui import QIcon, QPixmap
from PySide2.QtCore import QSettings
from PySide2.QtWidgets import QVBoxLayout
from PySide2.QtWidgets import QHBoxLayout
from PySide2.QtWidgets import QLabel
from PySide2.QtWidgets import QPushButton
from PySide2.QtWidgets import QStackedWidget
from PySide2.QtWidgets import QComboBox
from PySide2.QtWidgets import QCheckBox
from PySide2.QtWidgets import QGroupBox
from PySide2.QtWidgets import QLineEdit

from backimgw import BackImgW

import pyaudiowpatch as pyaudio
from google.cloud import speech
from openai import OpenAI

import queue
import threading
import os
import asyncio
loop = asyncio.get_event_loop()



RATE = 16000
CHUNK = int(RATE / 10)  # 100ms
DeviceIndexPick = None
openai_apikey = ""

class MainWindow(QMainWindow):

    mainstackw = None

    #widget 1
    #1.1
    DevicePickCombox = None
    DeviceIndexList = []
    DeviceRateList = []
    DeviceNamePick = None

    #1.2
    Areas = ["Java", "C++", "Python", "Android", "Network", "Algorithm"]
    ChoosenAreas = []
    AreaCheckBoxes = []

    #1.3
    #None

    #1.4
    api_linedit = None


    widget1_nextbtn = None


    #widget 2
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
                print("pick device: "+ DeviceNamePick)
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

        if key != None and key != "0":
            self.api_linedit.setText(key)
            self.api_linedit.home(True)
        else:
            self.api_linedit.clear()

    def Go_Interview(self):
        global openai_apikey
        openai_apikey = self.api_linedit.text()

        self.sava_OpenAI_key()

        self.mainstackw.setCurrentIndex(1)

    def control_speechtotext(self):
        if self.audioon:
            print("finisn speech to text")

            #send question to chatgpt as sonn as possible
            if self.ai_ans_label != None:
                self.chatgptshow_status_lock.acquire()
                self.chatgptshow_status = True
                self.chatgptshow_status_lock.release()
                self.chatgptshow_thread = threading.Thread(target = MainWindow.ask_openai, args = (self,))
                self.chatgptshow_thread.start()

            #end the speech to text
            self.audioon_lock.acquire()
            self.audioon = False
            self.audioon_lock.release()
            if self.MicStreaming != None:
                self.MicStreaming.finish()
            if self.recog_thread != None:
                self.recog_thread.join()

            self.audioControlbtn.setStyleSheet("background-color : white")
            self.audioControlbtn.setText("Start")

        else:
            print("start speech to text")

            #don show chatgpt ans now! start next task
            self.chatgptshow_status_lock.acquire()
            self.chatgptshow_status = False
            self.chatgptshow_status_lock.release()
            if self.chatgptshow_thread != None:
                self.chatgptshow_thread.join()

            self.recongtxt = ""
            #start speech to text
            self.audioon_lock.acquire()
            self.audioon = True
            self.audioon_lock.release()
            self.recog_thread = threading.Thread(target = MainWindow.recog, args = (self,))
            self.recog_thread.start()

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
        language_code = "en-US"  # a BCP-47 language tag


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
        if DeviceIndexPick != None:
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
            api_key = openai_apikey
        )

        questionHead = "Please answer in Chinese and then in English: "
        question = questionHead+self.recongtxt

        print(question)
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
            if self.chatgptshow_status == False:
                print("ans is cut off")
                return
            self.ai_ans = self.ai_ans + (chunk.choices[0].delta.content or "")
            self.ai_ans_label.setText(self.ai_ans)


#        for i in range(100):
#            if self.chatgptshow_status == False:
#                return
#            self.ai_ans = self.ai_ans + ("test test test test test")
#            self.ai_ans_label.setText(self.ai_ans)


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

        #1 widget   for sett audio device and area u want to choose, five tutorial and chatgpt api editor
        settingl = QHBoxLayout()
        settingl.setSpacing(20)
        settingl.setContentsMargins (40, 40, 40, 40) #left, top, right, bottom
        settingw.setLayout(settingl)

        #-----------------------------------------------------------
        device_area_l = QVBoxLayout()
        settingl.addLayout(device_area_l, 2)

        AudioDeviceChoosew = QGroupBox("Audio Device Selection")
        device_area_l.addWidget(AudioDeviceChoosew, 3)

        AreaChoosew = QGroupBox("Knowledge Domain Selection")
        device_area_l.addWidget(AreaChoosew, 7)

        #-----------------------------------------------------------
        info_api_l = QVBoxLayout()
        settingl.addLayout(info_api_l, 4)

        tutorialw = QGroupBox("Tutorial(Information before setting): ")
        info_api_l.addWidget(tutorialw, 5)

        chatgptapiw = QGroupBox("Enter your ChatGpt APi: ")
        info_api_l.addWidget(chatgptapiw, 1)

        self.widget1_nextbtn = QPushButton("Next")
        info_api_l.addWidget(self.widget1_nextbtn, 1)
        self.widget1_nextbtn.setMinimumHeight(90)
        self.widget1_nextbtn.clicked.connect(lambda: self.Go_Interview())



        #1.1 audio device choose
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


        #1.2 area choose
        AreaChoosel = QVBoxLayout()
        AreaChoosew.setLayout(AreaChoosel)

        for area in self.Areas:
            areacheckbox = QCheckBox(area)
            AreaChoosel.addWidget(areacheckbox)
            areacheckbox.clicked.connect(lambda: self.pickareas())
            self.AreaCheckBoxes.append(areacheckbox)

        self.pickareas()


        #1.3 tutorial
        infol = QVBoxLayout()
        tutorialw.setLayout(infol)

        infol.addSpacing(30)

        info_label = QLabel("here is infomation example: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        info_label.setWordWrap(True)
        infol.addWidget(info_label)


        #1.4 openapi
        apil = QVBoxLayout()
        chatgptapiw.setLayout(apil)

        apil.addSpacing(30)

        self.api_linedit = QLineEdit()
        self.api_linedit.setPlaceholderText("Enter API here")
        apil.addWidget(self.api_linedit)

        self.load_OpenAI_key()






        #2 widget
        interviewhelperl = QVBoxLayout()
        Helperw.setLayout(interviewhelperl)

        searchresultl = QHBoxLayout()
        interviewhelperl.addLayout(searchresultl)
        speechtotextl = QHBoxLayout()
        interviewhelperl.addLayout(speechtotextl)

        #------------------------------------------
        SpeechtoTextbox = QGroupBox("Speech to Text: ")
        speechtotextl.addWidget(SpeechtoTextbox)
        SpeechtoTextLayout = QVBoxLayout()
        SpeechtoTextbox.setLayout(SpeechtoTextLayout)

        self.recongtxtlabel = QLabel("Google speech to txt result")
        self.recongtxtlabel.setWordWrap(True)
        SpeechtoTextLayout.addSpacing(30)
        SpeechtoTextLayout.addWidget(self.recongtxtlabel)
        #------------------------------------------


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
        searchresultl.addWidget(LinkedQuestionBox)  #TODO



        Answersl = QVBoxLayout()
        searchresultl.addLayout(Answersl)
        #-----------------------------------------------
        ChatgptAnsBox = QGroupBox("Answer From ChatGPT: ")
        Answersl.addWidget(ChatgptAnsBox)

        ChatgptAnslayout = QVBoxLayout()
        ChatgptAnsBox.setLayout(ChatgptAnslayout)

        self.ai_ans_label = QLabel(self.ai_ans)
        self.ai_ans_label.setWordWrap(True)
        ChatgptAnslayout.addSpacing(30)
        ChatgptAnslayout.addWidget(self.ai_ans_label)
        #-----------------------------------------------
        PreAnsBox = QGroupBox("Prepared Question: ")
        Answersl.addWidget(PreAnsBox)

        PreAnsLayout = QVBoxLayout()
        PreAnsBox.setLayout(PreAnsLayout)

        self.pre_ans_label = QLabel(self.pre_ans)
        PreAnsLayout.addSpacing(30)
        PreAnsLayout.addWidget(self.pre_ans_label)


        self.chatgptshow_status_lock = threading.Lock()
        self.chatgptshow_status_lock.acquire()
        self.chatgptshow_status = False
        self.chatgptshow_status_lock.release()


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
