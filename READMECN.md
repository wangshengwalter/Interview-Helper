### 面试助手
------------
面试助手是一个基于QT开发的windows软件。它通过调用Google的语音转文字的API，将面试官的问题转化成文字，再通过OpenAI的API来回答这个问题。

**Table of Contents**

[TOCM]

[TOC]

## 改进
**如果你想添加其他功能或者帮助我改进这款软件**，请联系我的邮箱wangshengwalter@gmail.com，或者添加我的discord ID: shengwang。我十分欢迎您能够加入这个项目。

## 重要
面试助手调用了**Google Speech to Text**和**OpenAI**的**API**,你需要拥有这两个API的key才能够运行。Google将免费给予新注册的开发者账户400刀的额度，OpenAI将提供新注册的用户5刀的免费额度。这些额度将会让你使用这个软件很长很长时间，也许在你找到工作之后，你也只会花费你额度中的一两块钱。免费的额度毕竟不用白不用。
**如果你对这些API非常陌生，我将在下面详细教授如何获得调用API的密钥**，这非常简单。

我之后将会放弃使用Google的Speech To Text，改用GitHub中开源免费的whisper实时语音转文字的项目。同时，对模型进行改进，改善特定学科的专业名字的识别，比如说：计算机领域，电子工程领域，商科领域等。
楚辞之外，我也会放弃使用OpenAI的API，转而使用GitHub中开源免费的基于chatgpt网页版的伪OpenAI的API，原因是，免费，并且可以帮助无法使用chatgpt的国家。但是目前不清楚这会增加多少延迟，因为响应时间是这个面试助手的关键点。

## 快速安装（直接就可以使用）
面试助手提供可以直接运行的两个版本InterviewHelper_win_debug.exe和InterviewHelper.exe，前者将提供CLI打印关键信息，并帮助开发者进行debug,后者则隐藏CLI并直接运行软件。

## 编译安装（可以自己改代码，编译之后在运行软件）
本软件需要安装以下python库：
1. `pip install PySide2`
https://pypi.org/project/PySide2/
2. `pip install PyAudioWPatch`
https://pypi.org/project/PyAudioWPatch/
3. `pip install openai`
https://github.com/openai/openai-python
4. `pip install asyncio`
https://pypi.org/project/asyncio/
5. `pip install google-cloud-speech`
https://github.com/googleapis/python-speech

**之后使用python运行mainwindow.py或者下载QT Creator运行这个项目都没有问题**

## 使用方式（重要，无论你使用哪种安装方式）
1. 在release中选择你需要的版本，下载压缩包并在你想要运行软件的位置解压。
2. 将你下载的Google API密钥，也就是一个json文件，将名字改为：“google_key.json”，并放在res文件夹下。
3. 双击InterviewHelper运行。
4. 点击信任此软件。
5. 选择你的声音输出设备(需要支持audio loopback,什么是audio loopback？简单的来说就是将你喇叭的声音复制一份，发给这个软件，这样软件就能知道你的面试官问的是什么问题)。
6. 在软件右下角输入ChatGPT的API密钥。
7. 点击“Next”
8. 在面试官问话之前点击“start”（之后“start”按钮会变成“finish按钮”）
9. 在面试官问话结束时点击“finish”
10. 面试官的问题将会变成文字显示在软件下方
11. Chat GPT给出的回答将会显示在软件右上方
