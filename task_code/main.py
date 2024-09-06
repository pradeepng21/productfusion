import jwt
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from models.models import Base, User, Organisation, Role, Member
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text
from sqlalchemy import func
from typing import Optional
from datetime import datetime

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"

url = "mysql+pymysql://root:gdflmock12345@localhost:3306/dummy"
engine = create_engine(url)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

def create_jwt_token(user_id: int, expires_delta: timedelta = timedelta(hours=1)):
    expire = datetime.utcnow() + expires_delta
    to_encode = {"exp": expire, "user_id": user_id}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_jwt_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            return None
        return user_id
    except jwt.PyJWTError:
        return None


app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post('/signin')
def signin(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not bcrypt.verify(password, user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    access_token = create_jwt_token(user.id)
    refresh_token = create_jwt_token(user.id, expires_delta=timedelta(days=7))
    
    return {"access_token": access_token, "refresh_token": refresh_token}

@app.post('/signup')
def signup(email: str, password: str, org_name: str, db: Session = Depends(get_db)):
    hashed_password = bcrypt.hash(password)
    new_user = User(email=email, password=hashed_password, created_at=int(datetime.now().timestamp()))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    new_org = Organisation(name=org_name, created_at=int(datetime.now().timestamp()))
    db.add(new_org)
    db.commit()
    db.refresh(new_org)

    owner_role = Role(name="owner", org_id=new_org.id)
    db.add(owner_role)
    db.commit()
    db.refresh(owner_role)

    member = Member(user_id=new_user.id, org_id=new_org.id, role_id=owner_role.id, created_at=int(datetime.now().timestamp()))
    db.add(member)
    db.commit()
    
    return {"message": "User and Organization created successfully"}


@app.post('/reset-password')
def reset_password(email: str, new_password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password = bcrypt.hash(new_password)
    user.updated_at = int(datetime.now().timestamp())
    db.commit()

    return {"message": "Password updated successfully"}


@app.delete('/delete-member/{member_id}')
def delete_member(member_id: int, db: Session = Depends(get_db)):
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    db.delete(member)
    db.commit()
    
    return {"message": "Member deleted successfully"}


@app.put('/update-member-role/{member_id}')
def update_member_role(member_id: int, new_role_name: str, db: Session = Depends(get_db)):
    member = db.query(Member).filter(Member.id == member_id).first()
    member.updated_at=int(datetime.now().timestamp())
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    role = db.query(Role).filter(Role.org_id == member.org_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    role.name = new_role_name
    db.commit()
    
    return {"message": "Member role updated successfully"}


@app.get("/organizations/members/count")
def organization_members_count(db: Session = Depends(get_db)):
    query = """SELECT o.name, COUNT(m.user_id) AS member_count
        FROM organisation o
        LEFT JOIN member m ON o.id = m.org_id
        GROUP BY o.name;
        """
    result = db.execute(text(query))  # Use execute() for raw SQL
    members_count = result.fetchall()  # Fetch all rows

    # Format the result into a list of dictionaries
    formatted_result = [{"organization": row[0], "member_count": row[1]} for row in members_count]

    return formatted_result

@app.get("/organizations/roles/users/count")
def organization_role_users_count(db: Session = Depends(get_db)):
    query = """
        SELECT o.name AS organization, r.name AS role, COUNT(m.user_id) AS user_count
        FROM organisation o
        JOIN member m ON o.id = m.org_id
        JOIN role r ON m.role_id = r.id
        GROUP BY o.name, r.name;
    """
    result = db.execute(text(query))  # Execute raw SQL query
    role_user_counts = result.fetchall()  # Fetch all rows

    # Format the result into a list of dictionaries
    formatted_result = [
        {"organization": row[0], "role": row[1], "user_count": row[2]}
        for row in role_user_counts
    ]

    return formatted_result

@app.get("/organizations/members/count/filter")
def organization_members_count(
    from_time: Optional[int] = None,
    to_time: Optional[int] = None,
    status: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = """
        SELECT o.name, COUNT(m.user_id) AS member_count
        FROM organisation o
        LEFT JOIN member m ON o.id = m.org_id
        WHERE (:status IS NULL OR m.status = :status)
          AND (m.created_at BETWEEN :from_time AND :to_time OR :from_time IS NULL OR :to_time IS NULL)
        GROUP BY o.name;
    """
    
    # Default values if from_time or to_time are not provided
    from_time = from_time or 0
    to_time = to_time or 2147483647  # A large timestamp representing the future

    # Execute the query with the provided parameters
    result = db.execute(text(query), {"status": status, "from_time": from_time, "to_time": to_time})
    member_counts = result.fetchall()  # Fetch all rows

    # Format the result into a list of dictionaries
    formatted_result = [
        {"organization": row[0], "member_count": row[1]}
        for row in member_counts
    ]

    return formatted_result

# @app.get('/role-wise-users/{org_id}')
# def role_wise_users(org_id: int, db: Session = Depends(get_db)):
#     result = db.query(Role.name, func.count(Member.id)).join(Member).filter(Member.org_id == org_id).group_by(Role.name).all()
#     return {"role_wise_users": result}


# @app.get('/org-role-wise-users/{org_id}')
# def org_role_wise_users(org_id: int, from_time: int = None, to_time: int = None, status: int = None, db: Session = Depends(get_db)):
#     query = db.query(Role.name, func.count(Member.id)).join(Member).filter(Member.org_id == org_id)

#     if from_time:
#         query = query.filter(Member.created_at >= from_time)
#     if to_time:
#         query = query.filter(Member.created_at <= to_time)
#     if status is not None:
#         query = query.filter(Member.status == status)
    
#     result = query.group_by(Role.name).all()
#     return {"org_role_wise_users": result}


if __name__ == "__main__":
    try:
        import uvicorn
        uvicorn.run(app, host="194.163.169.162", port=8003)
    except Exception as e:
        print("Error in starting the FastAPI server: %s", e)
