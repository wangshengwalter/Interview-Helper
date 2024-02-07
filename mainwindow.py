# This Python file uses the following encoding: utf-8
import sys
from PySide2.QtWidgets import QApplication, QMainWindow
from PySide2.QtGui import QIcon, QPixmap
from PySide2.QtWidgets import QVBoxLayout
from PySide2.QtWidgets import QHBoxLayout
from PySide2.QtWidgets import QLabel
from PySide2.QtWidgets import QPushButton
from PySide2.QtWidgets import QStackedWidget
from PySide2.QtWidgets import QWidget
from PySide2.QtWidgets import QComboBox
from PySide2.QtWidgets import QCheckBox

import pyaudiowpatch as pyaudio
from google.cloud import speech

import queue
import threading
import os



RATE = 16000
CHUNK = int(RATE / 10)  # 100ms
DeviceIndexPick = None

class MainWindow(QMainWindow):
    #widget 1
    DevicePickCombox = None
    DeviceIndexList = []
    DeviceNamePick = None

    nextbtn_1 = None

    #widget 2
    Areas = ["Java", "C++", "Python", "Android", "Network", "Algorithm"]
    ChoosenAreas = []
    AreaCheckBoxes = []

    nextbtn_2 = None

    #widget 3
    recongtxt = "Speech to Text Result:"
    recongtxtlabel = None
    keywords = []
    keywordbtns = []

    audioControlbtn = None
    recog_thread = None
    audioon = False
    audioon_lock = None
    MicStreaming = None


    def refreshdevice(self):
        self.DevicePickCombox.clear()
        self.DeviceIndexList.clear()

        p = pyaudio.PyAudio()
        deviceinfo = p.get_loopback_device_info_generator()
        for loopback in deviceinfo:
            self.DevicePickCombox.addItem(loopback["name"])
            self.DeviceIndexList.append(loopback["index"])
#            print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
#            print(loopback["index"])
#            print(loopback["name"])
        p.terminate()

        print(self.DeviceIndexList)

        self.pickaudiodevice()

    def pickaudiodevice(self):
        if len(self.DeviceIndexList) != 0:
            DeviceNamePick = self.DevicePickCombox.currentText()
            global DeviceIndexPick
            DeviceIndexPick = self.DeviceIndexList[self.DevicePickCombox.currentIndex()]

            if DeviceNamePick == "" or DeviceIndexPick == None:
                self.nextbtn_1.setEnabled(False)
            else:
                print("pick device: "+ DeviceNamePick)
                print("pick device index: ", DeviceIndexPick)

    def pickareas(self):
#        print("areas changes")
        self.ChoosenAreas.clear()

        for checkbox in self.AreaCheckBoxes:
            if checkbox.isChecked():
                self.ChoosenAreas.append(checkbox.text())

#        print(self.ChoosenAreas)
        if len(self.ChoosenAreas) <= 0:
            self.nextbtn_2.setEnabled(False)
        else:
            self.nextbtn_2.setEnabled(True)


    def control_speechtotext(self):
        if self.audioon:
            print("finisn speech to text")
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
            self.audioon_lock.acquire()
            self.audioon = True
            self.audioon_lock.release()
            self.recongtxt = "Speech to Text Result:"
            self.recog_thread = threading.Thread(target = MainWindow.recog, args = (self,))
            self.recog_thread.start()
            self.audioControlbtn.setStyleSheet("background-color : red")
            self.audioControlbtn.setText("Finish")


    def refresh_recotext(self, responses: object) -> str:
        for response in responses:
            if not self.audioon:
                break
            if not response.results:
                continue

            result = response.results[0]

            if not result.alternatives:
                continue

            transcript = result.alternatives[0].transcript
            if not result.is_final:
                self.recongtxtlabel.setText(self.recongtxt+"\n"+transcript)
#                print("not final:  " + self.recongtxt+"\n"+transcript)
            else:
                self.recongtxt = self.recongtxt + "\n" + transcript
                self.recongtxtlabel.setText(self.recongtxt)
#                print("    final:  " + self.recongtxt)
#                if re.search(r"\b(exit|quit)\b", transcript, re.I):
#                    print("Exiting..")
#                    break

        return transcript

    def recog(self) -> None:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "GoogleSpeechtotxt\optical-unison-354222-c4e944f226f8.json"
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
            with MicrophoneStream(RATE, CHUNK) as stream:
                self.MicStreaming = stream
                audio_generator = stream.generator()
                requests = (
                    speech.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator
                )

                responses = client.streaming_recognize(streaming_config, requests)
                # Now, put the transcription responses to use.
                self.refresh_recotext(responses)


    def __init__(self):
        QMainWindow.__init__(self)
        self.setWindowTitle("InterView Helper")
        self.setWindowIcon(QIcon(QPixmap("interview.png")))

        mainstackw = QStackedWidget()
        self.setCentralWidget(mainstackw)

        AudioDeviceChoosew = QWidget()
        mainstackw.addWidget(AudioDeviceChoosew)
        AreaChoosew = QWidget()
        mainstackw.addWidget(AreaChoosew)
        Helperw = QWidget()
        mainstackw.addWidget(Helperw)


        #device choose widget #1 widget
        AudioDeviceChoosel = QVBoxLayout()
        AudioDeviceChoosew.setLayout(AudioDeviceChoosel)

        DevicePickTitle = QLabel("Please choose Output Audio Device")
        AudioDeviceChoosel.addWidget(DevicePickTitle)

        self.DevicePickCombox = QComboBox()
        AudioDeviceChoosel.addWidget(self.DevicePickCombox)
        self.DevicePickCombox.currentTextChanged.connect(lambda text: self.pickaudiodevice())

        refreshdevicebtn = QPushButton("Device Refresh")
        AudioDeviceChoosel.addWidget(refreshdevicebtn)
        refreshdevicebtn.clicked.connect(self.refreshdevice)

        self.nextbtn_1 = QPushButton("Next")
        AudioDeviceChoosel.addWidget(self.nextbtn_1)
        self.nextbtn_1.clicked.connect(lambda: mainstackw.setCurrentIndex(1))

        self.refreshdevice()




        #area choose widget #2 widget
        AreaChoosel = QVBoxLayout()
        AreaChoosew.setLayout(AreaChoosel)

        AreaPickTilte = QLabel("Please choose which area you want to take")
        AreaChoosel.addWidget(AreaPickTilte)

        for area in self.Areas:
            areacheckbox = QCheckBox(area)
            AreaChoosel.addWidget(areacheckbox)
            areacheckbox.clicked.connect(lambda: self.pickareas())
            self.AreaCheckBoxes.append(areacheckbox)


        self.nextbtn_2 = QPushButton("Next")
        AreaChoosel.addWidget(self.nextbtn_2)
        self.nextbtn_2.clicked.connect(lambda: mainstackw.setCurrentIndex(2))

        self.pickareas()



        #interview helper widget #3 widget
        interviewhelperl = QVBoxLayout()
        Helperw.setLayout(interviewhelperl)

        searchresultl = QHBoxLayout()
        interviewhelperl.addLayout(searchresultl)
        speechtotextl = QHBoxLayout()
        interviewhelperl.addLayout(speechtotextl)


        self.recongtxtlabel = QLabel("Google speech to txt result")
        self.audioControlbtn = QPushButton("Start")
        self.audioControlbtn.setStyleSheet("background-color : white")
        self.audioControlbtn.clicked.connect(lambda: self.control_speechtotext())
        self.audioon_lock = threading.Lock()
        self.audioon_lock.acquire()
        self.audioon = False
        self.audioon_lock.release()
        speechtotextl.addWidget(self.recongtxtlabel)
        speechtotextl.addWidget(self.audioControlbtn)



class MicrophoneStream:
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(self: object, rate: int = RATE, chunk: int = CHUNK) -> None:
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
    app.setWindowIcon(QIcon("interview.png"))

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
