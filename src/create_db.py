from models import User
from db import engine

def drop_db():
    print("Dropping tables...")
    User.metadata.drop_all(engine)



def create_db():
    print("Creating tables...")
    User.metadata.create_all(engine)



if __name__ == '__main__':
    print('Entering drop and create db')
    drop_db()
    create_db()
    print('Finished')
