# Tweeter

Tweeter is a Twitter clone built using Flask, SQLite, and Jinja templates. It allows users to sign up, log in, post tweets, view user profiles, and interact with tweets.

## Features

- User sign up and login functionality
- Posting and viewing tweets
- User profile pages
- Formatting tweets with bold, italic, and underline text
- Logout functionality

## Prerequisites

- Python 3.7 or higher
- Flask 2.0 or higher
- SQLite (included with Python)

## Installation

1. Clone the repository:

``
git clone <repository_url>
``

2. Navigate to the project directory:

``
cd tweeter
``

3. Create a virtual environment:

``
python3 -m venv venv
``

4. Activate the virtual environment:

``
source venv/bin/activate
``

5. Install the dependencies:

``
pip install -r requirements.txt
``

6. Run the application:

``
python main.py
``

7. Open your web browser and visit `http://localhost:5000` to access Tweeter.

## To-Do List

- Direct Messages (DMs) functionality
- Search functionality to find users and tweets
- Implement an algorithm for personalized tweet recommendations (similar to Twitter's algorithm)
- Add user profile picture upload functionality
- Enhance the design and styling of the application
- Implement retweets and likes functionality
- Integrate real-time updates using WebSocket (e.g., new tweets, notifications)
- Implement pagination for tweets on the home page and user profiles
- Implement trending topics and hashtags
- Add user settings and account management features
- Implement user authentication using OAuth (e.g., Google, Facebook, Twitter)
- Add support for multimedia content (images, videos) in tweets
- Implement user mentions and notifications
- Implement hashtag autocompletion and suggestions
- Improve security (e.g., password hashing, CSRF protection)
- Implement email notifications for important events (e.g., new followers, mentions)
- Perform code optimization and refactoring for better performance and maintainability

## Contributing

Contributions are welcome! If you have any suggestions, bug reports, or feature requests, please open an issue or submit a pull request.

## License

This project is licensed under the MIT License.
