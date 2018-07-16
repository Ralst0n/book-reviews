# Book Reviewer

Web Programming with Python and JavaScript
Book Reviewer allows a user to register and log in then rate & review 1 of 5000
different books.

Technical stuff
import.py takes 5000 rows from books.csv and puts them into the books table of
the database.

password.py creates a password class to more securly store hashed/salted versions
of user passwords and check those against the user typed password when they log in.

application.py provides routes to:
  use the search to find books by title, author or isbn
  navigate to a books detail page
  register for the app
  log in and out of the app
  access the book api to get basic info about a book by isbn
  use raw sql queries throughout via sqlalchemy db.execute

book.html includes:
  ratings and review count from good reads api
  placeholder ratings from this site
  thumbnails and descriptions from google books api
  a form to add a review to the book
  a reviews section showing the reviews left by other site users
