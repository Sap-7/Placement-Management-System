"""Idempotent demo-data seeder: preserves existing records and adds supplied students/companies."""
from datetime import date, datetime, timedelta
import random
from . import db
from .models import Admin, Course, Stream, StreamGroup, CompanyGroup, Student, Company, JobPosting, Application

BASE_NAMES = [
"Aarav Sharma","Ananya Das","Arjun Mukherjee","Ishita Roy","Rohan Banerjee","Priya Iyer","Aditya Nair","Sneha Chatterjee","Rahul Verma","Kavya Reddy","Sourav Ghosh","Meera Patel","Vikram Singh","Pooja Kulkarni","Abhishek Jain","Riya Sen","Karthik Raman","Tanvi Shah","Amit Kumar","Nandini Bose","Siddharth Rao","Aditi Malhotra","Debanjan Dutta","Neha Kapoor","Sanjay Yadav","Shreya Pillai","Manish Gupta","Diya Saha","Varun Menon","Swati Mishra","Aniket Paul","Madhuri Joshi","Pranav Deshmukh","Tanya Agarwal","Suman Mondal","Akash Choudhury","Ritika Bansal","Kunal Bhattacharya","Payal Dasgupta","Harsh Vardhan","Sanjana Krishnan","Nikhil Saxena","Pallavi Tripathi","Soumyadeep Pal","Anjali Naidu","Deepak Thakur","Moumita Kundu","Yash Mehta","Rashmi Shetty","Kaushik Ghosal"]
ADDITIONAL_NAMES = [
"Snehasis Mondal","Aritra Mondal","Arijit Debnath","Soham Mondal","Ahnik Purkait","Saptarshi Garai","Nayan Singha","Dipjyoti Dash","Pratyay Sarkar","Agnish Saha","Anisha Ghosh","Md. Kabir","Rishi Sanyal","Naman Ray","Pabitra Chatterjee","Subhadeep Kanthali","Ayushman Ghosh","Ayan Das",
"Rachana Mondal","Suchetana Chattopadhyay","Shifa Tasnim","Sheza Anam","Anusha Mukhopadhyay","Arti Kumari","Shiuli Khatun","Sornali Sen","Ambika Agarwal","Deb Dwaipayan Ray","Shreya Banerjee","Tohida Khatun","Prarthona Bandyopadhyay","Maitree Pratihar","Samarpita Das","Tiyasa Purkait","Sk Julia","Sulagna Jana","Jarina Hossain","Riya Majumdar","Ritushree Mandal","Ruma Halder","Ankita Das","Humaira Wasim","Ankita Ghosal","Banasri Adak","Anindita Barman","Farhat Jahan","Alisha Nzrin","Kajori Majumdar","Disha Biswas","Arpita Chatterjee","Abir Biswas",
"Santanu Das","Surajit Das","Arti Kumari","Soumyajit Pal","Subhrajit Naskar","Pritam Sarkar","Ayan Sarkar","Dupchen Lama","Anirudh Modi","Kumar Vikramaditya Mondal","Sk Md Ashfaque","Balaaditya Kamal","Sornali Sen","Kushal Bera","Ayushman Devnath","Fardeen Akhtar","Irfan Mondal","Samya Das","Soham Dhara","Pranjal Mondal","Samim Aktar"]
BASE_COMPANIES = [("Tata Consultancy Services","tcs.example.in"),("Infosys","infosys.example.in"),("Wipro","wipro.example.in"),("HCLTech","hcltech.example.in"),("Tech Mahindra","techmahindra.example.in"),("Tata Motors","tatamotors.example.in"),("Larsen & Toubro","larsentoubro.example.in"),("Tata Elxsi","tataelxsi.example.in"),("NVIDIA India","nvidia.example.in"),("Texas Instruments India","ti.example.in")]
ADDITIONAL_COMPANIES = [("Reliance Industries","reliance.example.in"),("Hindustan Unilever","hul.example.in"),("Bharat Electronics Limited","bel.example.in"),("Tata Steel","tatasteel.example.in"),("Mahindra & Mahindra","mahindra.example.in"),("Flipkart","flipkart.example.in"),("Amazon India","amazonindia.example.in"),("Cognizant","cognizant.example.in"),("Accenture India","accenture.example.in"),("L&T Technology Services","ltts.example.in")]

def seed():
    admin = Admin.query.filter_by(username="admin").first()
    if not admin:
        admin = Admin(username="admin"); admin.set_password("admin123"); db.session.add(admin)
    course = Course.query.filter_by(name="B.Tech").first()
    if not course:
        course = Course(name="B.Tech"); db.session.add(course); db.session.flush()
    stream_names = ["Computer Science", "Electronics & Telecommunication", "Electrical", "Mechanical", "Civil", "Information Technology"]
    streams = []
    for n in stream_names:
        st = Stream.query.filter_by(name=n, courseid=course.courseid).first()
        if not st:
            st = Stream(name=n, courseid=course.courseid); db.session.add(st); db.session.flush()
        streams.append(st)
    db.session.flush()
    # Add the requested names without duplicating an existing person with the same name.
    existing_names = {s.name.strip().casefold() for s in Student.query.all()}
    next_roll = 1
    for s in Student.query.all():
        if s.roll.startswith("JU2026") and s.roll[6:].isdigit(): next_roll = max(next_roll, int(s.roll[6:]) + 1)
    all_names = BASE_NAMES + ADDITIONAL_NAMES
    for name in all_names:
        if name.strip().casefold() in existing_names: continue
        i = next_roll; next_roll += 1
        st = streams[(i - 1) % len(streams)]
        email_stub = f"student{i:03d}"
        student = Student(roll=f"JU2026{i:03d}", name=name.strip(), personalemail=f"{email_stub}@example.in",
            collegeemail=f"{email_stub}@jadavpuruniversity.example.in", CGPA=round(6.5 + (i % 35)/10, 2),
            marks_10=75 + (i*3)%24, marks_12=70 + (i*7)%28, diplomamarks=None,
            DOB=date(2003+i%3, 1+i%12, 1+i%27), Gender="Female" if i%2==0 else "Male",
            mobileno=f"9{(700000000+i):09d}", streamid=st.deptid, courseid=course.courseid,
            yearofgraduation=2027, is_approved=True)
        student.set_password("student123"); db.session.add(student); existing_names.add(name.strip().casefold())
    db.session.flush()
    # Student groups consist of streams.
    group_specs = {"Software":["Computer Science","Information Technology"],"Circuital Core":["Electronics & Telecommunication","Electrical"],"Mechanical Core":["Mechanical"],"Civil Core":["Civil"],"Management":stream_names}
    for name, members in group_specs.items():
        group = StreamGroup.query.filter_by(groupname=name).first()
        if not group: group = StreamGroup(groupname=name); db.session.add(group)
        group.streams = [s for s in streams if s.name in members]
    db.session.flush()
    groups_by_name = {g.groupname: g for g in StreamGroup.query.all()}
    for student in Student.query.all():
        if student.stream.name in ("Computer Science", "Information Technology"):
            student.group = groups_by_name["Software"]
        elif student.stream.name in ("Electronics & Telecommunication", "Electrical"):
            student.group = groups_by_name["Circuital Core"]
        elif student.stream.name == "Mechanical":
            student.group = groups_by_name["Mechanical Core"]
        elif student.stream.name == "Civil":
            student.group = groups_by_name["Civil Core"]
    db.session.flush()
    all_company_specs = BASE_COMPANIES + ADDITIONAL_COMPANIES
    for i, (name, domain) in enumerate(all_company_specs, 1):
        c = Company.query.filter_by(companyname=name).first()
        if not c:
            c = Company(companyname=name, companymail=f"placement@{domain}", fulltimeCTCannual=8+i*1.2, sixmonthpaypermonth=35000+i*2000)
            c.set_password("company123"); db.session.add(c); db.session.flush()
        # Fill missing email/password values on legacy records only when necessary.
        if not c.companymail: c.companymail=f"placement@{domain}"
        if not c.password_hash: c.set_password("company123")
        if not c.streams:
            if i in (1,2,3,4,5,16,17,18,19): c.streams=[streams[0],streams[1],streams[2],streams[5]]
            elif i in (6,7,14,15,20): c.streams=[streams[1],streams[2],streams[3],streams[4]]
            else: c.streams=[streams[0],streams[1],streams[2],streams[5]]
        if not c.poc:
            c.poc = Student.query.order_by(Student.roll).offset((i-1)%Student.query.count()).first()
        if not c.jobs:
            for n, title in enumerate([f"{c.companyname} Graduate Engineer", f"{c.companyname} Intern"], 1):
                db.session.add(JobPosting(companyid=c.companyid,title=title,description=f"Sample {title} opportunity. Review eligibility and apply before the deadline.",deadline=datetime.now().replace(second=0,microsecond=0)+timedelta(days=14+n),min_cgpa=7.0 if n==1 else 6.0))
    db.session.flush()
    company_group_specs = {
      "Software":["Tata Consultancy Services","Infosys","Wipro","HCLTech","Tech Mahindra","Flipkart","Amazon India","Cognizant","Accenture India"],
      "Management":["Tata Consultancy Services","Infosys","Larsen & Toubro","Reliance Industries","Hindustan Unilever","Mahindra & Mahindra"],
      "Mechanical Core":["Tata Motors","Larsen & Toubro","Tata Steel","Mahindra & Mahindra","L&T Technology Services"],
      "Circuital Core":["Tata Elxsi","NVIDIA India","Texas Instruments India","Bharat Electronics Limited","L&T Technology Services"],
      "Civil Core":["Larsen & Toubro","Tata Steel","Reliance Industries"]}
    for name, names in company_group_specs.items():
        group = CompanyGroup.query.filter_by(groupname=name).first()
        if not group: group=CompanyGroup(groupname=name); db.session.add(group)
        group.companies = Company.query.filter(Company.companyname.in_(names)).all()
    db.session.commit()

