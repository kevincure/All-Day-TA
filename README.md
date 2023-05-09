README Building a "virtual teaching assistant" for your class
Kevin Bryan, University of Toronto, March 2023 (updated May 8 2023)

These instructions help you deploy your own custom TA for your classes, which can be queried at will.  Is it reasonably straightforward to set up - you do not need to change one line of code, but you do need to run two python programs and deploy one program to the cloud.  I'll show you how below.  You have been given the following files: app.py, EmbedDocuments.py, ChopDocuments.py, ChunkAudio.py, TranscribeAudio.py, APIkey.txt, settings.txt, requirements.txt, .dockerignore, Dockerfile, and in the templates subfolder, a file titled index.html.  The only files you will edit are APIkey.txt and settings.txt.

1) Get your documents.  Anything you have as a class doc or optional reading or related reading - pdf, doc, docx, .tex, txt all work.  For pdf's documents you can't copy/paste from won't load right, so you'll need to use an online free OCR software to convert the pdf to something readable first.  A lot of economics working papers (including mine!) are in a format that does really bad (famously the letter 'f' won't copy/paste right) - a few errors aren't terrible, but basically, anything you have which isn't in pdf, you should use the other format.  For your slides, write one to two paragraphs of each slide and save this document as a txt file.  For your lecture audio, we will handle the transcription at high quality (much higher than Zoom or Youtube) in the code.  Related text that is "near" each other is easier to find - for instance, if you syllabus has a table listing when each class is from the first to the last, and what is due when, it will absolutely be searchable perfectly.  If it requires five pages of reading to know what, say, the "last" assignment due in a semester is, this will be much harder using our method.

2) Once you have all your documents, name them in a way that is easy to follow: e.g., "Bryan and Guzman - Entrepreneurial Migration", "Agarwal Gans Goldfarb - Power and Prediction", "Class Handout - Startup Venture Financing", "Class Lecture Transcription - Experimentation (Class 1)", "CDL Advanced Entrepreneurship Class Transcript - Class 2 Pricing for Startups" and so on.  Ensure the syllabus has "Syllabus" somewhere in the title.

3) Get your OpenAI API key and your Google Cloud API key.  The OpenAI key is what you need to make calls to GPT.  The Google Cloud key is for running your web-based TA app.  Both need a credit card.  For Open AI, you'll pay about 3 cents for each document you embed and 36 cents per hour of audio you transcribe - this is a one time cost - plus about $1 per 200-250 queries by students.  Google Cloud hosting will be very inexpensive.  Here is the instructions:

OpenAI API:
a. https://openai.com/blog/openai-api
b. If you don't have an OpenAI account, create one by providing the required information.
c. Once you have an account and have requested API access, wait for approval from OpenAI (usually instant).
d. Log in.  Click on your avatar in the top right-hand corner of the dashboard.  Select View API Keys. Click Create new secret key.  Write this down somewhere!  You won't be able to see it again without regenerating a different key.  So create a file called APIkey.txt , paste your key and nothing else, and save it in the folder where you will be storing your "virtual TA documents".

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

4) If you are going to transcribe your lectures, you need to install a local program called ffmpeg. For Windows, I find it easiest to download Scoop then install it as below.  Once you have one of the linked "package managers" involved, you just need to open a command prompt (in admin mode) and type the relevant line.
# on MacOS using Homebrew (https://brew.sh/)
brew install ffmpeg
# on Windows using Chocolatey (https://chocolatey.org/)
choco install ffmpeg
# on Windows using Scoop (https://scoop.sh/)
scoop install ffmpeg

5) Create your settings.  
In your "virtual TA" folder, place all of your documents in the Documents subfolder. Open settings.txt in the main folder and edit.  I would leave the last two entries as is:

classname=Creative Destruction Lab (CDL) Intro
professor=Joshua Gans and Alberto Galasso
assistantname=CDL Virtual Teaching Assistant
assistants=the teaching assistants (TAs) Ronald and Eugenia and the course manager/Program Coordinator Melika
classdescription=a Summer 2023 graduate course in entrepreneurship at the Rotman School of Management
instructions=I am an experimental virtual TA for your course in entrepreneurship.  I have been trained with all of your readings, course materials, lecture content, and slides. I am generally truthful, but be aware that there is a large language model in the background and hallucinations are possible. The more precise your question, the better an answer you will get. You may ask me questions in the language of your choice.  If "an error occurs while processing", ask you question again: the servers we use to process these answers are also in beta.
num_chunks=8
filedirectory=Documents


classname is passed to the AI as a description of who it is act as a TA for.  professor is the name of the folks teaching the class.  assistantname is what will appear at the top of the html page your students see.  instructions are for the students; you may write what you want here and it will display when the students load the virtual TA page.  filedirectory is the case sensitive name of the subdirectory where your documents are held.  num_chunks controls how much text is sent to the server; you can't go much higher than 8, while going lower than 8 will reduce costs at the risk of reducing answer accuracy.

6) You do not need to touch app.yaml, Dockerfile, .dockerignore, and requirements.txt files or the files in the templates subfolder.  

7) Install python if you haven't already.  I generally write in PyTorch.

8) Open a command window (cmd on Windows - if you use Mac or Linux, I will assume you can translate these instructions).  cd the directory to your virtual TA folder.  type "pip install -r requirements.txt" and hit enter.  This makes sure you have all the libraries you need.

9) If you have audio to transcribe, place the raw mp4/mp3/wav audio files in the subfolder Raw Audio.  Run ChunkAudio (in the command window, py ChunkAudio.py).  This will separate your audio into five minute blocks - the whisper API will not transcribe files with a size larger than 25MB each.  Then run TranscribeAudio (py TranscribeAudio.py).  This will create high quality transcriptions of your audio using the Whisper API.  The "professor" and "classname" keys in the settings.txt file help ensure your name is transcribed correctly and that the class context is interpreted right.  It will take roughly 3 minutes per hour of audio.  

10) If you transcribed audio, go into the "transcriptions" folder and look at each of the large text files ending with concatenated_transcript.txt.  These are the full transcripts of each of your original audio files. I give a quick glance and delete any intro/outro/homework discussion plus any students names from people I may have called on.  Once you are happy, paste these into the Documents subfolder.  You can delete everything else in the folder transcriptions at this point if you like.

11) Place all of the your other txt, doc, pdf, tex, docx files in the Documents subfolder as well.

12) Now we prepare all the text.  Run ChopDocuments.py (py ChopDocuments.py in the command window).  You will see your files list one by one.  Once this programs ends, you have a file called "xxx-originaltext.csv" in your virtual TA folder.  Open it and scan through to make sure nothing scanned strangely - again, pdfs are the biggest danger here.

13) If the text looks good, in the same command window, run EmbedDocuments.py (py EmbedDocuments.py). This will take a few minutes if you have many documents - it is putting every few sentences into 1500-dimensional vector space using a rolling window of roughly 150 words.  The basic idea here is that when your students write a query, we will try to find chunks of text with a similar meaning by looking at the cosine similarity of the embedded query and all of the possible chunks of text. We'll do a bunch of stuff in the background to make the query as likely as possible to find the right text, then pass all that text to GPT3.5 with, essentially, instructions to try to truthfully find the answer to the user query in the context here.

14) Now run CreateFinalData (py CreateFinalData.py in the same command window).  This will take all of the text chunks and embeddings, and create two big files which are used by the AI to find the text we need.  If you want to add new content later, just re-chop-and-embed the new files and run this again.  

15) Now let's test before deploying (these directions are slightly different on Mac or Linux - you can easily google or ask GPT the difference). Open a command prompt.  Change to the directory where your virtual TA is stored.  Open a virtual environment in python by typing py -m venv env and pressing enter, then env\Scripts\Activate.bat and press enter, then set FLASK_APP=app and press enter, then flask run and hit enter.  You should see  

* Serving Flask app 'app'
* Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
* Running on http://127.0.0.1:5000
Press CTRL+C to quit

Open a browser and type http://localhost:5000/ - your TA should be up and working.

Alternatively, you can click run_AI.bat and then open localhost:5000 in your browser; if there are errors, this will just crash, in which case do the steps above so you can see errors.  You can also see in the command window as you ask questions a lot of what is going on in the background of the code, which is fun!

16) You can ask questions naturally. The code works really well even if you don't say exactly what lecture or reading or whatever you are asking about, but of course, the more precise the question, the more precise the answer.  If you type "m: " and some concept, it will generate a multiple choice question on that concept (e.g., "m: venture fundraising with SAFEs"); when the student answers, it will also explain why the answer was correct or not.  The system is not a "chat" per se - it does not remember the old conversation - but it does try to identify follow-up questions when they are asked and hence to retain the relevant context.  This works 95% now, but it's a short-run problem: once GPT4's API falls in price, we'll use that, and GPT4 is very accurate for this use case.  Mathematics currently fails almost always - again, this is a short-run problem which is solved by GPT4; however, GPT4 is 10x the cost right now and so not deployed.

17) Now to "deploy" the app, or to make it web-accessible.  In the cmd window, again go to your virtual TA directory. Type
gcloud init 
and go through a few settings.  Then type
gcloud config set run/region us-east1
to configure your server for the east coast of N. America.  Then
gcloud run deploy --source .
You will be asked to name your service - it doesn't matter as long as it is all lower case. You should after a few minutes see a web link something like https://paknf-dl7kadk33lya-ue.a.run.app .  You will probably need more memory, so at this stage, so go to https://console.cloud.google.com/run , click on your project, click "Edit & Deploy New Revision" in the center-top, and under "Capacity" change Memory to 2GB.  This should be way more than enough.

18) Now you should be good - click on your link from above and play around with it! Any time you want to add new content, just put the new documents in the same documents folder you originally used, run ChopDocuments and EmbedDocuments again, and redeploy as in step 15.  The code automatically adds your new documents to the already-embedded text so you only have to pay for embeddings once.

19) I do not have any way of making students log in at this stage, so in theory your site is open to anyone who has a browser and the link.  We are building a front-end and hosted server space here at Rotman, with student log-in, to solve this problem and the annoyance of needing your own cloud server.  You may want to go to billing in your OpenAI and Google Cloud accounts and set a spending cap just in case.

20) What if you have two classes you want to use this tool for?  Just create a second root folder and do everything else as above!  You'll wind up with a second deployed app custom for your second class.
