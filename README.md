README Building a "virtual teaching assistant" for your class
Kevin Bryan, University of Toronto, originally March 2023 (updated Feb 20 2024)

These instructions help you deploy your own custom TA for a university class, which can be queried at will.  Is it reasonably straightforward to set up - you do not need to change one line of code, but you do need to run three python programs and deploy one program to the cloud.  I'll show you how below.  You have been given the following files: app.py, EmbedDocuments.py, ChopDocuments.py, ChunkAudio.py, TranscribeAudio.py, APIkey.txt, CohereAPI.txt, settings.txt, requirements.txt, .dockerignore, Dockerfile, and in the templates subfolder, a file titled index.html.  The only files you will edit are APIkey.txt CohereAPI.txt, and settings.txt.

It will cost about 20 bucks and a couple hours of time to set up your content.  I highly recommend rewriting your syllabus to specifically list your assignments in order, to include a document with definitions and acronyms from your class, and to follow the instructions below on transcripts carefully.  You may want to consider adding documents with student Q&As where you gave particularly good answers, or documents full of example worked-out problems - that is, imagine the content you would need to give you TA and make sure the AI also has it!

Cost-wise, on a running basis, the current system costs about 4.5 US cents per question.  We average roughly 50 questions per student per semester (with skew, of course), or $2.25.  Including training costs for a sufficiently large cost barely changes this figure.  And note: this cost will go down over time, and quality will go up. If you are cash-constrained, checked "gpt-4" to "gpt-4-turbo-preview" on the line "response_question = query_openai(content, 1000, "gpt-4", 0.2, instructions)" in app.py.  This results in a minor performance degrade, but cuts costs to 2.4 US cents per question.

To make sure you understand how a system like this works, it's essentially a complex "RAG", or Retrieval Augmented Generation.  That is, it takes all of your documents, uses a bunch of pre- and post-processing tricks to find where in your documents the answer to a query might be, passes the most likely sources on to a very advanced LLM, then returns an answer.  The goal?  Give *more* precise answers than the internet/Google, then public LLMs, and than your TA, taking advantage of the fact that the system has access to reams of your own documents.  The more content you give this system, particularly content that you agree with, the better.

1) Get your documents.  Anything you have as a class doc or optional reading or related reading - pdf, doc, docx, tex, txt, ppt, pptx all work.  For PDFs, check in advance whether you can copy and paste from your document - if not, this code won't be able to see it.  Your option in that case is to OCR or print then OCR the PDF first.  A lot of economics working papers (including mine!) are in a format that does really bad (famously the letter 'f' won't copy/paste right) - a few errors aren't terrible, but basically, anything you have which isn't in pdf, you should use the other format.  For your slides, write one to two paragraphs of each slide and save this document as a txt file.  For your lecture audio, we will handle the transcription at high quality (much higher than Zoom or Youtube) in the code using something called Whisper.  Related text that is "near" each other is easier to find - for instance, if you syllabus has a table listing when each class is from the first to the last, and what is due when, it will absolutely be searchable perfectly.  If it requires five pages of reading to know what, say, the "last" assignment due in a semester is, this will be much harder using our method.

2) Once you have all your documents, name them in a way that is easy to follow: e.g., "Bryan and Guzman - Entrepreneurial Migration", "Agarwal Gans Goldfarb - Power and Prediction", "Class Handout - Startup Venture Financing", "Class Lecture Transcription - Experimentation (Class 1)", "CDL Advanced Entrepreneurship Class Transcript - Class 2 Pricing for Startups" and so on.  Ensure the syllabus has "Syllabus" somewhere in the title. THIS IS VERY IMPORTANT.

3) Get your OpenAI API key, Cohere API key, and your Google Cloud API key.  The OpenAI key is what you need to make calls to GPT.  The Google Cloud key is for running your web-based TA app.  Both need a credit card.  For Open AI, you'll pay about $1 for each document you embed and 36 cents per hour of audio you transcribe - this is a one time cost - plus about $1 per 25 queries by students.  Google Cloud hosting will be very inexpensive.  Here is the instructions:

OpenAI API:
a. Go to https://openai.com/blog/openai-api
b. If you don't have an OpenAI account, create one by providing the required information.
c. Once you have an account and have requested API access, wait for approval from OpenAI (usually instant).
d. Log in.  Click on your avatar in the top right-hand corner of the dashboard.  Select View API Keys. Click Create new secret key.  Write this down somewhere!  You won't be able to see it again without regenerating a different key.  Paste this key and nothing else into "APIkey.txt"

Cohere API key:
a. Go to https://dashboard.cohere.com/welcome/login
b. Create an account.
c. Click "Get API Key" in your Dashboard.
d. Click "+ New Production Key".  Paste this and nothing else into CohereAPI.txt.

Google Cloud SDK API:
To gain access to the Google Cloud SDK API and download the necessary software, follow these steps:
a. Go to Google Cloud's website: https://cloud.google.com/
b. Click on the "Get started for free" button to create a new account or sign in to your existing Google account.
c. After signing in, go to the Google Cloud Console: https://console.cloud.google.com/
d. Create a new project or select an existing one.
e. Enable the Google Compute Engine API (https://console.cloud.google.com/flows/enableapi?apiid=compute)
f. Make sure billing is enabled (https://cloud.google.com/billing/docs/how-to/verify-billing-enabled)
g. Download and install the Google Cloud SDK (https://cloud.google.com/sdk/docs/install)
h. Choose the appropriate version for your operating system and follow the provided installation instructions.
i. After installation, open a terminal or command prompt and run "gcloud init" to initialize the SDK.
j. Follow the prompts to authenticate your Google Cloud account and set up your default project.  You can select whatever lowercase name you want - it doesn't matter.  We'll come back to this when we "deploy" your site to the web.

4) If you are going to transcribe audio from your lectures, you need to install a local program called ffmpeg. For Windows, I find it easiest to download Scoop then install it as below.  Once you have one of the linked "package managers" involved, you just need to open a command prompt (in admin mode) and type the relevant line.
# on MacOS using Homebrew (https://brew.sh/)
brew install ffmpeg
# on Windows using Chocolatey (https://chocolatey.org/)
choco install ffmpeg
# on Windows using Scoop (https://scoop.sh/)
scoop install ffmpeg

For Windows, this is three lines. 
1) Open a Powershell console (type Powershell in the search bar on Windows if you don't know how to find it)
2) type "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
3) Type A for all and press enter
4) type "Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression"
5) type "scoop install ffmpeg"

5) Create your settings.  
In your "virtual TA" folder, place all of your documents in the Documents subfolder. Open settings.txt in the main folder and edit. 

classname=Intermediate Football Theory
professor=Rob Gronkowski and Tom Brady
assistantname=Virtual Teaching Assistant
assistants=the teaching assistants (TAs) Jules and Coach, and the course manager Mayo
classdescription=a Summer 2023 graduate course in football theory at the Rotman School of Management
instructions=I am an experimental virtual TA for your course in football theory.  I have been trained with all of your readings, course materials, lecture content, and slides. I am generally truthful, but be aware that there is a large language model in the background and hallucinations are possible. The more precise your question, the better an answer you will get. You may ask me questions in the language of your choice.  If "an error occurs while processing", ask you question again: the servers we use to process these answers are also in beta.

classname is passed to the AI as a description of who it is act as a TA for.  professor is the name of the folks teaching the class.  assistantname is what will appear at the top of the html page your students see.  instructions are for the students; you may write what you want here and it will display when the students load the virtual TA page. 

6) You do not need to touch app.yaml, Dockerfile, .dockerignore, and requirements.txt files or the files in the templates subfolder.  

7) Install python if you haven't already (https://www.python.org/downloads/windows/ - get Python 3.11 in order to make dependencies work).  I generally write code in PyCharm.

8) Open a command window (cmd on Windows - if you use Mac or Linux, I will assume you can translate these instructions. If you aren't familiar with this, open it in Administrator Mode).  cd the directory to your virtual TA folder.  type "pip install -r requirements.txt" and hit enter.  This makes sure you have all the libraries you need.

9) If you have audio to transcribe, place the raw mp4/mp3/wav files in the subfolder Raw Audio.  You can put your video files here if you like - it will still work.  First, run the program PrepareAudio 
	In the command window, from the base file directory, type "py PrepareAudio.py"
This will take your audio and video and reduce its size to what's necessary for audio transcription.  
Then run the program TranscribeAudio
	In the command window, type "py TranscribeAudio.py"
This will create high quality transcriptions of your audio using the Whisper API.  The "professor" and "classname" keys in the settings.txt file help ensure your name is transcribed correctly and that the class context is interpreted right.  It will take roughly 3 minutes per hour of audio, and costs 36 cents per hour of audio. 

10) If you transcribed audio, go into the "transcriptions" folder and look over each file.  These are the full transcripts of each of your original audio files. I give a quick glance and delete any intro/outro/homework discussion plus any students names from people I may have called on.  Give it a quick scan and also make sure any technical terms or similar don't need to be cleaned up.  Once you are happy, cut and paste these transcript files into the Documents subfolder.  You can delete everything else in the folder transcriptions at this point if you like.

11) Place all of your other txt, doc, pdf, tex, docx, ppt, pptx files in the Documents subfolder as well.  On your syllabus or other files where data is in tables or setups where the order isn't obvious, it may be worth a short edit to make it "machine readable" - the AI will only see the txt, not how it is organized on a page, so consider this when thinking about whether, say, assignment dates or similar will be found if you don't have that visual structure. 

12) For any files that are locked, such as certain PDFs, you will need to extract the text yourself. One way to check is to open the pdf, select some txt, and to copy and paste it - if the copy/paste doesn't work, then your file won't open correctly. There are many ways to do this - e.g., print it and then scan it to OCR, and save the resulting text to a .txt file.  Unlocked doc, docx, txt, tex, ppt, pptx files should be fine unless they are saved in a crazy character set. I haven't had this issue come up yet. 

12) Now we prepare all the text.  Run ChopDocuments.py 
	In the command window type "py ChopDocuments.py"
You will see your files list one by one.  Once this programs ends, you have a file called "xxx-originaltext.csv" in your Textchunks folder.  Open it and scan through to make sure nothing scanned strangely - again, pdfs are the biggest danger here.  ChopDocuments also generates short summaries appended to the top of each chunk of text, which helps the eventual code "find" where the answer to a student query is.  This costs about 10-20 cents per document.  All of your Documents will be moved to "Already Chopped Documents". 

13) If the text looks good, in the same command window, run EmbedDocuments.py
	In the command window, type "py EmbedDocuments.py"
This will take a few minutes if you have many documents - it is putting every few sentences into 1500-dimensional vector space using a rolling window of roughly 400 words.  The basic idea here is that when your students write a query, we will try to find chunks of text with a similar meaning by looking at the cosine similarity of the embedded query and all of the possible chunks of text. We'll do a bunch of stuff in the background to make the query as likely as possible to find the right text, then pass all that text to GPT with, essentially, instructions to try to truthfully find the answer to the user query in the context here.

14) Now run CreateFinalData 
	In the command window, type "py CreateFinalData.py
This will take all of the text chunks and embeddings, and create two big files which are used by the AI to find the text we need.  If you want to add new content later, just place it into Documents, and run steps 12-14. 

15) Now let's test before deploying (these directions are slightly different on Mac or Linux - you can easily google or ask GPT the difference). Open a command prompt.  Change to the directory where your virtual TA is stored.  
	In the command window, type "py app.py"

* Serving Flask app 'app'
* Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
* Running on http://127.0.0.1:5000
Press CTRL+C to quit

	Open a browser and type http://localhost:5000/
When you do this, your TA should be up and running!  Try a few questions.

16) You can ask questions naturally. The code works really well even if you don't say exactly what lecture or reading or whatever you are asking about, but of course, the more precise the question, the more precise the answer. Mathematics currently fails almost always - again, this is a short-run problem which is getting better every month.  The system currently is very much biased against answering questions that are not directly in the class content, so the more content you provide, the better!  

17) Now to "deploy" the app, or to make it web-accessible.  In the cmd window, again go to your virtual TA directory. Type
	gcloud init 
and go through a few settings.  Then type
	gcloud config set run/region us-east1
to configure your server for the east coast of N. America.  Then
	gcloud run deploy --source .
You will be asked to name your service - it doesn't matter as long as it is all lower case. If you have previously deployed, make sure you use the same "Service name" when you are asked. If this is the first time you are deploying, you should after a few minutes see a web link something like https://paknf-dl7kadk34kya-ue.a.run.app.  You will probably need more memory, so at this stage, so go to https://console.cloud.google.com/run, click on your project, click "Edit & Deploy New Revision" in the center-top, and under "Capacity" change Memory to 2GB.  This should be way more than enough.

18) Now you should be good - click on your link from above and play around with it! Any time you want to add new content, just put the new documents in the same documents folder you originally used, run ChopDocuments and EmbedDocuments again, and redeploy as in step 17.  The code automatically adds your new documents to the already-embedded text so you only have to pay for embeddings once.

19) What if you have two classes you want to use this tool for?  Just create a second root folder and do everything else as above!  You'll wind up with a second deployed app custom for your second class.

20) There is also code to create an automated Question Bank.  Updates to this Q&A to handle that case coming shortly.
