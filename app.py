from flask import Flask, request, render_template, redirect, url_for, send_file
import os
import spacy
import re
from langchain_community.llms import Ollama

app = Flask(__name__)

# Configure upload and download folders
UPLOAD_FOLDER = "uploads"
DOWNLOAD_FOLDER = "downloads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["DOWNLOAD_FOLDER"] = DOWNLOAD_FOLDER

# Ensure the upload and download folders exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Function to extract information from CV text
nlp = spacy.load("en_core_web_sm")

# Function to extract information from CV text
def extract_cv_info(cv_text):
    cv_data = {
        "name": None,
        "contact": {"email": None, "phone": None},
        "education": [],
        "experience": [],
        "skills": []
    }

    # Extract name using spaCy's NER
    doc = nlp(cv_text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            cv_data["name"] = ent.text
            break

    # Extract email and phone using regex
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    phone_pattern = r"\+?\d[\d -]{8,12}\d"
    cv_data["contact"]["email"] = re.findall(email_pattern, cv_text)[0]
    cv_data["contact"]["phone"] = re.findall(phone_pattern, cv_text)[0]

    # Extract education
    education_section = re.search(r"Education:(.*?)(Experience:|Skills:|$)", cv_text, re.DOTALL)
    if education_section:
        education_lines = education_section.group(1).strip().split("\n")
        cv_data["education"] = [line.strip() for line in education_lines if line.strip()]

    # Extract experience
    experience_section = re.search(r"Experience:(.*?)(Skills:|$)", cv_text, re.DOTALL)
    if experience_section:
        experience_lines = experience_section.group(1).strip().split("\n")
        cv_data["experience"] = [line.strip() for line in experience_lines if line.strip()]

    # Extract skills
    skills_section = re.search(r"Skills:(.*?)$", cv_text, re.DOTALL)
    if skills_section:
        skills_lines = skills_section.group(1).strip().split("\n")
        cv_data["skills"] = [line.strip() for line in skills_lines if line.strip()]

    return cv_data


# Load LLaMA 2 model using Ollama
llm = Ollama(model="llama2", temperature=0.7)

# Function to generate a recommendation letter
def generate_recommendation_letter(cv_data, job_description):
    # Prepare the prompt
    prompt = f"""
    I need a cover letter based on their CV and the job description provided. The letter should emphasize the candidate's relevant skills, 
    experience, and achievements while tailoring the content to the requirements of the job. Below are the details:

    CV:
    Name: {cv_data['name']}
    Email: {cv_data['contact']['email']}
    Phone: {cv_data['contact']['phone']}

    Education:
    {', '.join(cv_data['education'])}

    Experience:
    {', '.join(cv_data['experience'])}

    Skills:
    {', '.join(cv_data['skills'])}

    Job Description:
    {job_description}
    """

    # Generate the recommendation letter using LLaMA 2
    recommendation_letter = llm(prompt)
    return recommendation_letter

# Home page
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Check if files are uploaded
        if "cv_file" not in request.files or "job_description_file" not in request.files:
            return "Please upload both CV and Job Description files."

        cv_file = request.files["cv_file"]
        job_description_file = request.files["job_description_file"]

        # Save uploaded files
        cv_path = os.path.join(app.config["UPLOAD_FOLDER"], cv_file.filename)
        job_description_path = os.path.join(app.config["UPLOAD_FOLDER"], job_description_file.filename)
        cv_file.save(cv_path)
        job_description_file.save(job_description_path)

        # Read files
        with open(cv_path, "r") as file:
            cv_text = file.read()
        with open(job_description_path, "r") as file:
            job_description = file.read()

        # Extract CV data
        cv_data = extract_cv_info(cv_text)

        # Generate recommendation letter
        recommendation_letter = generate_recommendation_letter(cv_data, job_description)

        # Save the generated letter to a file
        letter_filename = "cover_letter.txt"
        letter_path = os.path.join(app.config["DOWNLOAD_FOLDER"], letter_filename)
        with open(letter_path, "w") as file:
            file.write(recommendation_letter)

        # Redirect to result page with the generated letter filename
        return redirect(url_for("result", filename=letter_filename))

    return render_template("index.html")

# Result page
@app.route("/result")
def result():
    filename = request.args.get("filename")
    letter_path = os.path.join(app.config["DOWNLOAD_FOLDER"], filename)
    with open(letter_path, "r") as file:
        recommendation_letter = file.read()
    return render_template("result.html", letter=recommendation_letter, filename=filename)

# Download the generated cover letter
@app.route("/download/<filename>")
def download(filename):
    return send_file(
        os.path.join(app.config["DOWNLOAD_FOLDER"], filename),
        as_attachment=True,
        download_name=filename
    )

if __name__ == "__main__":
    app.run(debug=True)