import requests
from bs4 import BeautifulSoup
from enum import Enum
try:
   from account import GSAccount
except ModuleNotFoundError:
   from .account import GSAccount

try:
   from course import GSCourse
except ModuleNotFoundError:
   from .course import GSCourse

class ConnState(Enum):
    INIT = 0
    LOGGED_IN = 1

class GSConnection():
    '''The main connection class that keeps state about the current connection.'''
        
    def __init__(self):
        '''Initialize the session for the connection.'''
        self.session = requests.Session()
        self.state = ConnState.INIT
        self.account = None

    def login(self, email, pswd):
        '''
        Login to gradescope using email and password.
        Note that the future commands depend on account privilages.
        '''
        init_resp = self.session.get("https://www.gradescope.com/")
        parsed_init_resp = BeautifulSoup(init_resp.text, 'html.parser')
        for form in parsed_init_resp.find_all('form'):
            if form.get("action") == "/login":
                for inp in form.find_all('input'):
                    if inp.get('name') == "authenticity_token":
                        auth_token = inp.get('value')

        login_data = {
            "utf8": "✓",
            "session[email]": email,
            "session[password]": pswd,
            "session[remember_me]": 0,
            "commit": "Log In",
            "session[remember_me_sso]": 0,
            "authenticity_token": auth_token,
        }
        login_resp = self.session.post("https://www.gradescope.com/login", params=login_data)
        if len(login_resp.history) != 0:
            if login_resp.history[0].status_code == requests.codes.found:
                self.state = ConnState.LOGGED_IN
                self.account = GSAccount(email, self.session)
                return True
        else:
            return False

    def get_account(self):
        '''
        Gets and parses account data after login. Note will return false if we are not in a logged in state, but 
        this is subject to change.
        '''
        if self.state != ConnState.LOGGED_IN:
            return False # Should raise exception
        # Get account page and parse it using bs4
        account_resp = self.session.get("https://www.gradescope.com/account")
        parsed_account_resp = BeautifulSoup(account_resp.text, 'html.parser')

        # Get instructor course data
        instructor_courses = parsed_account_resp.find('h1', class_ ='pageHeading').next_sibling
        # TODO: Brittle selection of course names
        if instructor_courses.text == 'Everything you need to know about Gradescope is in our Getting Started guide.':
            instructor_courses = instructor_courses.next_sibling

        for course in instructor_courses.find_all('a', class_ = 'courseBox'):
            shortname = course.find('h3', class_ = 'courseBox--shortname').text
            name = course.find('h4', class_ = 'courseBox--name').text
            cid = course.get("href").split("/")[-1]
            year = None
            print(cid, name, shortname)
            for tag in course.parent.previous_siblings:
                if 'courseList--term' in tag.get("class"):
                    year = tag.string
                    break
            if year is None:
                return False # Should probably raise an exception.
            self.account.add_class(cid, name, shortname, year, instructor = True)

        try:
            student_courses = parsed_account_resp.find('h1', class_ ='pageHeading', string = "Student Courses").next_sibling
            for course in student_courses.find_all('a', class_ = 'courseBox'):
                shortname = course.find('h3', class_ = 'courseBox--shortname').text
                name = course.find('h4', class_ = 'courseBox--name').text
                cid = course.get("href").split("/")[-1]
                print(cid, name, shortname)

                for tag in course.parent.previous_siblings:
                    if tag.get("class") == "courseList--term pageSubheading":
                        year = tag.body
                        break
                if year is None:
                    return False # Should probably raise an exception.
                self.account.add_class(cid, name, shortname, year)
        except:
            print('No student classes')

# THIS IS STRICTLY FOR DEVELOPMENT TESTING :( Sorry for leaving it in.
if __name__=="__main__":
    conn = GSConnection()
    conn.login(os.getenv('GRADESCOPE_EMAIL'), os.getenv('GRADESCOPE_PASSWORD'))
    print(conn.state)
    conn.get_account()
    
    for cnum in conn.account.instructor_courses:
        course = conn.account.instructor_courses[cnum]
        print('\n### Course Name: ' + course.name)
        print(str(course))

        course._force_load_data()

        print('\n--Assignments--')
        print(course.assignments)
        for _, assign in course.assignments.items():
            print(str(assign))

        print('\n--Roster--')
        print(course.roster)
        for _, person in course.roster.items():
            print(str(person))

        print('\n--Grades--')
        print(course.grades)
        for _, person in course.grades.items():
            for _, grade in person.items():
                print(str(grade))

        print()
        print(course.get_grades())

        
