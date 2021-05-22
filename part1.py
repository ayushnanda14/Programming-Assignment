from flask import Flask, request, render_template, redirect, Response
from flask_restplus import Api, Resource, fields
from werkzeug.middleware.proxy_fix import ProxyFix

import mysql.connector as msc
from datetime import date, datetime, timedelta

import enum
import bcrypt as bc
from random import random
import jwt
from functools import wraps

class Status(enum.Enum):
    not_started = 'Not started'
    in_progress = 'In progress'
    finished = 'Finished'

IS_AUTHORIZED = False

try:
    db = msc.connect(
        host='localhost',
        user='root',
        password='root',
        database='tododb'
    )
    db1 = msc.connect(
        host='localhost',
        user='root',
        password='root',
        database='client_db'
    )
    cs = db.cursor()
    cs1 = db1.cursor()

except:
    db = msc.connect(
        host='localhost',
        user='root',
        password='root'
    )
    cs = db.cursor()
    cs.execute('CREATE DATABASE tododb;')
    cs.execute('USE tododb;')
    cs.execute('''CREATE TABLE todos_list(
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    task varchar(50) NOT NULL,
                    due_by date,
                    status varchar(15));''')
    query = "INSERT INTO todos_list (task, due_by, status) VALUES(%s, %s, %s)"
    vals = [
        ('Build an API', '2021-05-21', 'In progress'),
        ('?????', '2021-05-30', 'Not started'),
        ('profit!', '2021-05-19', 'Finished')
    ]
    cs.executemany(query, vals)
    db.commit()
    db.close()
    db = msc.connect(
        host='localhost',
        user='root',
        password='root',
        database='tododb'
    )
    db1 = msc.connect(
        host='localhost',
        user='root',
        password='root',
        database='client_db'
    )
    cs = db.cursor()
    cs1 = db1.cursor()


app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-KEY'
    }
}
api = Api(
    app,
    version='1.0',
    title='TodoMVC API',
    description='A simple TodoMVC API',
    authorizations=authorizations,
    security=['apikey'],
)


ns = api.namespace('todos', description='TODO operations')
apins = api.namespace('getapitoken', description='Get Access Token')

todo = api.model('Todo', {
    'id': fields.Integer(readonly=True, description='The task unique identifier'),
    'task': fields.String(required=True, description='The task details'),
    'Due by': fields.Date(required=True, description='The due date of the task (YYYY-MM-DD)'),
    'Status': fields.String(required=True, description='The task status with values - [Not started, In progress, Finished]', enum=[i.value for i in Status], attribute='Status.value')
})


def jsonify_data(data):
    res = {
        'id': data[0],
        'task': data[1],
        'Due by': str(data[2]),
        'Status': str(data[3])
    }
    return res

app.config['SECRET_KEY'] = 'hellothisisthepassword'
def read_access(f):
    @wraps(f)
    def func(*args, **kwargs):
        jwtoken = None
        if 'X-API-KEY' in request.headers:
            jwtoken = request.headers['X-API-KEY']
        if not jwtoken:
            return {'message': 'No token found.', 'error': 'No token found'}, 401
        
        cs1.execute('USE client_db')
        cs1.execute('SELECT * FROM scopes WHERE userid = %s', (jwtoken,))
        res_len = len([i for i in cs1])
        if res_len == 0:
            return {'message': "User doesn't exist or doesn't have enough permissions", 'error': 'NOt enough permissions'}, 401
        return f(*args, **kwargs)

    return func


def write_access(f):
    @wraps(f)
    def func(*args, **kwargs):
        jwtoken = None
        if 'X-API-KEY' in request.headers:
            jwtoken = request.headers['X-API-KEY']
        if not jwtoken:
            return {'message': 'No token found.', 'error': 'No token found'}, 401

        cs1.execute('USE client_db')
        cs1.execute('SELECT * FROM scopes WHERE userid = %s AND scope=%s', (jwtoken, 'W'))
        res_len = len([i for i in cs1])
        if res_len == 0:
            return {'message': "User doesn't exist", 'error': 'No user found'}, 401
        return f(*args, **kwargs)

    return func

class TodoDAO(object):
    def __init__(self):
        cs.execute("SELECT * FROM todos_list;")
        self.counter = len([i for i in cs])

    def get_all(self):
        cs.execute("SELECT * FROM todos_list;")
        todos = [jsonify_data(i) for i in cs]
        print(todos)
        self.counter = len(todos)
        return todos, self.counter

    def get(self, id):
        todos = self.get_all()[0]
        for todo in todos:
            if todo['id'] == id:
                return todo
        api.abort(404, "Todo {} doesn't exist".format(id))

    def create(self, data):
        try:
            if self.conv(data['Status']) == None:
                raise ValueError
        except ValueError:
            api.abort(404, 'Invalid Status Parameter')
            return None
        todo = data
        query = "INSERT INTO todos_list VALUES(%s, %s, %s, %s)"
        self.counter += 1
        vals = (self.counter, data['task'],
                str(data['Due by']), data['Status'])
        cs.execute(query, vals)
        db.commit()
        todo['id'] = self.counter
        return self.conv_str_to_enum(todo)

    def update(self, id, data):
        todo = self.get(id)
        todo.update(data)
        
        query = "UPDATE todos_list SET task = %s, due_by = %s, status = %s WHERE id = %s"
        vals = (todo['task'], todo['Due by'], todo['Status'].value if type(todo['Status']) != str else todo['Status'], id)
        cs.execute(query, vals)
        db.commit()
        return self.conv_str_to_enum(todo)

    def delete(self, id):
        query = "DELETE FROM todos_list WHERE id = %s"
        val = (id,)
        cs.execute(query, val)
        db.commit()
        self.counter -= 1

    def conv(self, val):
        for i in Status:
            if val == i.value:
                return i
        return None

    def conv_str_to_enum(self, data):
        data['Status'] = self.conv(data['Status'])
        return data


DAO = TodoDAO()


@ns.route('/')
class TodoList(Resource):
    '''Shows a list of all todos, and lets you POST to add new tasks'''
    @api.doc(security='apikey')
    @ns.doc('list_todos')
    @ns.marshal_list_with(todo)
    @read_access
    def get(self):
        '''List all tasks'''
        try:
            new_list = [DAO.conv_str_to_enum(i) for i in DAO.get_all()[0]]
            return new_list
        except AttributeError:
            api.abort(404, 'Invalid Status Parameter')
            return None

    @api.doc(security='apikey')
    @ns.doc('create_todo')
    @ns.expect(todo)
    @ns.marshal_with(todo, code=201)
    @write_access
    def post(self):
        '''Create a new task'''
        return DAO.create(api.payload), 201


@ns.route('/<int:id>')
@ns.response(404, 'Todo not found')
@ns.param('id', 'The task identifier')
class Todo(Resource):
    '''Show a single todo item and lets you delete them'''
    @api.doc(security='apikey')
    @ns.doc('get_todo')
    @ns.marshal_with(todo)
    @read_access
    def get(self, id):
        '''Fetch a given task'''
        try:
            data = DAO.get(id)
            return DAO.conv_str_to_enum(data)
        except AttributeError:
            api.abort(404, 'Invalid Status Parameter')
            return None

    @api.doc(security='apikey')
    @ns.doc('delete_todo')
    @ns.response(204, 'Todo deleted')
    @write_access
    def delete(self, id):
        '''Delete a task given its identifier'''
        DAO.get(id)
        DAO.delete(id)
        return {'message': "Deletion Successful"}, 204

    @api.doc(security='apikey')
    @ns.expect(todo)
    @ns.marshal_with(todo)
    @write_access
    def put(self, id):
        '''Update a task given its identifier'''
        pl = api.payload
        if 'Status' in pl:
            pl['Status'] = DAO.conv(pl['Status'])
        
        a = DAO.update(id, pl)

        if 'Status' in pl:    
            a['Status'] = pl['Status']
        return a

    @api.doc(security='apikey')
    @ns.param('status', 'The task status', _in='query', required=True, enum=[i.value for i in Status])
    @ns.expect(todo)
    @ns.marshal_with(todo)
    @write_access
    def post(self, id):
        '''Update a task given its identifier'''
        args = request.args
        if 'status' in args:
            try:
                a = DAO.update(id, {'Status': DAO.conv(args['status'])})
                return {'id': a['id'], 'task': a['task'], 'Due by': a['Due by'], 'Status': DAO.conv(args['status'])}
                # return a

            except ValueError:
                api.abort(400, 'Invalid Status Parameter')
                return None
        else:
            api.abort(400, 'Post not possible without status parameter')


@ns.route('/due')
@ns.response(400, 'No query string provided or no due date provided.')
class DueTasks(Resource):
    '''Shows a list of all due todos'''
    @api.doc(security='apikey')
    @ns.param('due_date', 'The due date', _in='query', required=True)
    @ns.doc('list_due_todos')
    @ns.marshal_with(todo)
    @read_access
    def get(self):
        '''List all the due tasks with respect to the given date'''
        args = request.args

        if "due_date" in args:
            due_date = args["due_date"]
        else:
            api.abort(400, "No query string provided or no due date provided.")
            return '', 400

        def conv_date(s):
            dr = list(map(int, s.split('-')))
            return date(dr[0], dr[1], dr[2])

        return [DAO.conv_str_to_enum(i) for i in DAO.get_all()[0] if conv_date(i['Due by']) == conv_date(due_date)]


@ns.route('/overdue')
class OverdueTasks(Resource):
    '''Shows a list of all overdue todos'''
    @api.doc(security='apikey')
    @ns.doc('list_overdue_todos')
    @ns.marshal_list_with(todo)
    @read_access
    def get(self):
        '''List all overdue tasks'''
        def conv_date(s):
            dr = list(map(int, s.split('-')))
            return date(dr[0], dr[1], dr[2])

        return [DAO.conv_str_to_enum(i) for i in DAO.get_all()[0] if conv_date(i['Due by']) < date.today()]

@ns.route('/finished')
class FinishedTasks(Resource):
    '''Shows a list of all finished todos'''
    @api.doc(security='apikey')
    @ns.doc('list_finished_todos')
    @ns.marshal_list_with(todo)
    @read_access
    def get(self):
        '''List all finished tasks'''
        return [DAO.conv_str_to_enum(i) for i in DAO.get_all()[0] if i['Status'] == 'Finished']

    
@apins.route('/')
class TokenHandler(Resource):
    @ns.param('username',description='Enter your Username', _in='query', required=True)
    @ns.param('password', description='Enter your Password', _in='query', required=True)
    @ns.param('scope', description='Enter the scope you would like access', _in='query', required=True, enum= ['Read', "Write"])
    def get(self):
        args = request.args
        if 'username' not in args or 'password' not in args:
            api.abort(401,"No username or password provided")
            return
        if not (args['username'] == 'username' and args['password'] == 'password'):
            api.abort(404,"Invalid username or password")
            return
        DATETIME = datetime.utcnow() + timedelta(hours=24)
        token = jwt.encode({'user': args['username'], 'exp': DATETIME}, app.config['SECRET_KEY'])
        cs1.execute('select * from scopes')
        n = len(cs1.fetchall())
        dtval = str(DATETIME).split('.')[0]
        print(dtval)
        cs1.execute('insert into scopes (userid, scope, expires_in) values (%s,%s,%s)',(token,args['scope'][0],dtval))
        db1.commit()
        return {'accesstoken': token}


if __name__ == '__main__':
    app.run(debug=True)
