This file will serve as instructions for this project that you're about to do. As an overview, what I'm trying to do here is to not like this actually so I have a an automated telegram news channel for AI related news it was built in n but now I want to convert the entire workflow as this to code And so these are the instructions that will help you do this right, making sure that everything is preserved because there are a lot of important and delicate things in the workflow. 

So to start off the workflow is not a single workflow but it's a two-part system The first part parses the articles and normalizes articles from different sources into a three field payload we have article text which is the entire raw content of the article. We have article URL, which is just the URL to that specific article,  the article date, which is the exact date of this article that was published, as well as images and videos arrays, which are arrays that contain images and videos we were able to parse from the page (if none found, we leave them empty). In this workflow, we have Currently two sites that we parse the workflow set up to every ten minutes we trigger the parsing of this website. We compare the latest article from that list page to all the articles that we already have in our Notion database and if it's a new article then we go on to parse that actual article so we parse that URL and we are trying to extract information from it. 

We also have a few rss feeds. 

The second workflow deals with the data, and converts it to a ready to go post. We have a set of ai nodes each doing their own task:
1. summarizer - takes the raw article text, and strips it of any html trash, and extracts a single main point out of it
2. relevance checker - this blocks any articles we deem not important for our channel. 
3. Duplicate control - checks the article against existing articles in the notion db (i imagine this can be done in a better way, maybe without ai)
4. post writer - writes the full post

Now a lot of other nodes you will see deal with one of the most difficult parts i have had, which is getting a relevant image for the post. https://find-image.simple-flow.co is my microservice that finds the best fitting image. 

And we actually have a 3rd workflow, which is responsible for rewriting the post in russian, and posting to the ru lang version channel.

In the project you will see the 3 json files for those 3 workflows, with all the settings and prompts. and im also pasting the repos for my ai parser, and image finder microservices so you can understand how they work. Im open to suggestions on how to improve these two, or if you think we can do this better without them, that also works with me. 

ai parser repo: https://github.com/nik-ti/ai_parser
image finder repo: https://github.com/nik-ti/image-finder

I want you to recreate this channel with code, and improve anything you see fit to increase effeciency and lower costs. 

IMPORTANT: Pay attention to the node setups. One big thing is that each post goes to my admin channel first, and i get to press approve or decline. we have to make sure we dont actually post to the main channel by acciden throughout this process

ive build this channel to the best of my limitied skills, and in the limited n8n. with code, and you writing it we have an ability to make this a much better workflow. I want to be able to easily setup these news channels for others too