import os
import time
import random
from openai import OpenAI
from dotenv import load_dotenv
from requests_oauthlib import OAuth1
import requests
import re



def extract_poll_options(story_text):
    """
    Extracts up to 3 clean poll options from a story.
    - Strips "Option X:" labels
    - Clips each to 25 characters max (required by X API)
    """
    options = []
    matches = re.findall(r"Option \d:\s*(.+)", story_text)
    
    for i in range(3):
        if i < len(matches):
            clean = matches[i].strip()
            clipped = clean[:20]  # hard limit for X poll API
            options.append(clipped)
        else:
            options.append(f"Choice {i+1}.strip()[:20]")  # fallback short default
    return options
# Load environment variables from .env
load_dotenv()

# Initialize the OpenAI-style client configured for x.ai’s Grok‑3 API v2.
client = OpenAI(
    base_url="https://api.x.ai/v1",
    api_key=os.getenv("XAI_API_KEY"),
)

# X (formerly Twitter) credentials from your environment.
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
# X API v2 endpoint for creating tweets (posts)
X_API_CREATE_POST_URL = "https://api.x.com/2/tweets"

def generate_story(prompt):
    """
    Generate an adventure story using the Grok-3 API.
    Returns the generated text or an empty string if an error occurs.
    """
    try:
        messages = [
            {
                "role": "system", 
                "content": "You are a highly intelligent AI story generator that creates engaging, interactive 'Choose Your Own Adventure' narratives. At the end of each post you end with 3 options labeled Option 1: Option 2: Option 3: for polling reasons. these options MUST be less than 25 characters"
            },
            {"role": "user", "content": prompt},
        ]
        completion = client.chat.completions.create(
            model="grok-3-mini",  # or "grok-3-mini-fast-beta"
            reasoning_effort="high",
            messages=messages,
            temperature=0.6,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Error generating story: {e}")
        return ""



def post_tweet_with_poll(tweet_text, poll_options, poll_duration_minutes):
    """
    Post a tweet (X post) with a poll using the X API v2.
    Builds the payload that includes tweet text and a poll object.
    Uses OAuth1 for authentication.
    """
    payload = {
        "text": tweet_text,
        "poll": {
            "options": poll_options,
            "duration_minutes": poll_duration_minutes
        }
    }
    auth = OAuth1(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    response = requests.post(X_API_CREATE_POST_URL, json=payload, auth=auth)
    if response.status_code != 201:
        raise Exception(f"Request returned an error: {response.status_code} {response.text}")
    return response.json()

def get_poll_results(tweet_id):
    """
    Retrieves poll results for the given tweet ID.
    Queries the tweet along with its poll details via the X API.
    """
    url = f"https://api.x.com/2/tweets?ids={tweet_id}&tweet.fields=attachments&expansions=attachments.poll_ids&poll.fields=options,voting_status"
    auth = OAuth1(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    response = requests.get(url, auth=auth)
    if response.status_code != 200:
        raise Exception(f"Error fetching poll results: {response.status_code} {response.text}")
    data = response.json()
    polls = data.get("includes", {}).get("polls", [])
    if polls:
        poll = polls[0]
        if poll.get("voting_status") != "closed":
            print("Poll is still active.")
            return None
        options = poll.get("options", [])
        if not options:
            return None
        # Determine the winning option by vote count.
        winning_option = max(options, key=lambda opt: opt.get("votes", 0))
        return winning_option.get("label")
    else:
        print("No poll data found; defaulting to first option.")
        return None

def main():
    # Set initial parameters.
    poll_duration_current = 5  # starting poll duration in minutes
    
    poll_duration_increment = 1 #random.randint(5,180)   each post's poll duration increases by this many minutes
    previous_data = None

    # Initial prompt for the adventure narrative.
    prompt = (
        "You are an AI narrating an interactive, never-ending 'Choose Your Own Adventure' story. "
        "The protagonist, X, stranded on Mars, embarks on a mysterious journey back to Earth that subtly hints at a cosmic secret called 'grokGantua'. "
        "Craft a 150-225 word narrative in second-person perspective describing X's challenges and enigmatic discoveries. poll options must be 25 characters max"
        "End with three numbered choices labeled 'Option 1:', 'Option 2:' and 'Option 3:' for X's next move. a poll option can never be more than 25 characters. the options 1 2 and 3 can not be over 25 characters long. use one word if needed"
    )

    # Infinite loop that never ends.
    while True:
        print("\n--- New Post ---")
        # Use the winning poll option from the previous iteration to craft a new prompt.
        if previous_data:
            winning_option = previous_data.get("winning_option")
            if not winning_option:
                winning_option = previous_data.get("poll_options", ["Option 1 missing"])[0]
            prompt = (
                f"Continue the adventure narrative using the previous poll's winning option: '{winning_option}'. "
                "Craft a new 150-225 word segment in second-person perspective that builds on the previous story and ends "
                "with three new choices labeled 'Option 1:', 'Option 2:' and 'Option 3:' for X's next move."
            )
        
        # Generate the story using the Grok‑3 API.
        story_text = generate_story(prompt)
        print("\nGenerated Story:\n", story_text)
        
        # Extract poll options from the story.
        poll_options = extract_poll_options(story_text)
        print("\nExtracted Poll Options:")
        for idx, option in enumerate(poll_options, 1):
            print(f"Option {idx}: {option}")
        
        # Build tweet text; ensure it fits within X's character limit (280 characters).
        poll_prompt = "vote on X's next move"
        max_story_length = 2500 - len(poll_prompt) - 50
        truncated_story = story_text if len(story_text) <= max_story_length else story_text[:max_story_length] + "..."
        tweet_text = f"{truncated_story}\n\n{poll_prompt}"
        print("\nTweet Text:\n", tweet_text)
        
        # Use the current poll duration for this iteration.
        poll_duration_minutes = poll_duration_current
        print(f"\nPoll Duration (minutes): {poll_duration_minutes}")
        
        # Post the tweet with the poll.
        try:
            post_response = post_tweet_with_poll(tweet_text, poll_options, poll_duration_minutes)
            tweet_id = post_response.get("data", {}).get("id")
            print("\n✅ Post created successfully with ID:", tweet_id)
        except Exception as e:
            print("\n❌ Error posting tweet:", e)
            break
        
        # The delay before the next post is 4 minutes longer than the current poll duration.
        next_delay_seconds = (poll_duration_minutes + 4) * 60
        print(f"\nWaiting for {next_delay_seconds} seconds before fetching poll results...")
        time.sleep(next_delay_seconds)
        
        # Retrieve poll results.
        try:
            winning_label = get_poll_results(tweet_id)
            if not winning_label:
                print("Poll results unavailable; defaulting to first option.")
                winning_label = poll_options[0]
            print(f"\nWinning Poll Option: {winning_label}")
        except Exception as e:
            print("Error retrieving poll results:", e)
            winning_label = poll_options[0]
        
        # Save data for the next iteration.
        previous_data = {
            "winning_option": winning_label,
            "poll_options": poll_options,
        }
        
        # Increase the poll duration for the next iteration.
        poll_duration_current += poll_duration_increment
        print(f"\nPoll duration for next post will be: {poll_duration_current} minutes.")

if __name__ == "__main__":
    main()
