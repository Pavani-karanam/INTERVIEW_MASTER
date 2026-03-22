import google.generativeai as genai
import json
import re
import os

def configure_ai(api_key):
    genai.configure(api_key=api_key)

def get_model():
    return genai.GenerativeModel('gemini-2.0-flash', generation_config={"temperature": 0.9})

def generate_questions(job_role, company, interview_type, resume_text="", num_questions=10):
    """Generate interview questions using Google Gemini AI."""
    model = get_model()

    type_description = {
        "technical": "technical/coding questions relevant to the job role",
        "hr": "HR/behavioral questions about teamwork, leadership, conflict resolution, etc.",
        "mixed": "a mix of technical and HR/behavioral questions"
    }

    prompt = f"""You are an expert interviewer at {company}. Generate exactly {num_questions} interview questions for a {job_role} position.

Question type: {type_description.get(interview_type, 'mixed')}

{"Resume/Background of the candidate: " + resume_text[:2000] if resume_text else "No resume provided."}

IMPORTANT: Return your response as a valid JSON array of objects with these fields:
- "question": the interview question text
- "category": either "Technical" or "HR/Behavioral"
- "difficulty": one of "Easy", "Medium", "Hard"

Example format:
[
  {{"question": "Tell me about yourself and why you want to work at {company}.", "category": "HR/Behavioral", "difficulty": "Easy"}},
  {{"question": "Explain the concept of Object-Oriented Programming.", "category": "Technical", "difficulty": "Medium"}}
]

Generate exactly {num_questions} questions. Ensure all questions are uniquely different from each other, highly diverse, and cover a wide range of different concepts within the topic. DO NOT repeat any questions. Return ONLY the JSON array, no other text."""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Extract JSON from response
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            questions = json.loads(json_match.group())
            return questions[:num_questions]
        else:
            return _fallback_questions(job_role, interview_type, num_questions)
    except Exception as e:
        print(f"AI Question Generation Error: {e}")
        return _fallback_questions(job_role, interview_type, num_questions)


def evaluate_answer(question, user_answer, job_role, company):
    """Evaluate a user's answer using Google Gemini AI."""
    model = get_model()

    if not user_answer or user_answer.strip() == "":
        return {
            "score": 0,
            "feedback": "No answer was provided. Try to attempt every question, even if you're unsure.",
            "strengths": [],
            "improvements": []
        }

    prompt = f"""You are an expert interviewer at {company} evaluating a candidate for a {job_role} position.

Question: {question}
Candidate's Answer: {user_answer}

Evaluate the answer and return a JSON object with these fields:
- "score": a number from 0 to 10 (10 being perfect)
- "feedback": a 2-3 sentence constructive feedback
- "strengths": an array of 1-2 strengths in the answer
- "improvements": an array of 1-2 areas for improvement

Return ONLY the JSON object, no other text."""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            result['score'] = max(0, min(10, float(result.get('score', 5))))
            return result
        else:
            return _fallback_evaluation(user_answer)
    except Exception as e:
        print(f"AI Evaluation Error: {e}")
        return _fallback_evaluation(user_answer)


def generate_overall_feedback(job_role, company, questions_data):
    """Generate overall interview performance feedback with detailed skill analysis."""
    model = get_model()

    qa_summary = ""
    for i, q in enumerate(questions_data, 1):
        qa_summary += f"\nQ{i} ({q.get('category', 'General')}, {q.get('difficulty', 'Medium')}): {q.get('question', '')}\n"
        qa_summary += f"Answer: {q.get('user_answer', 'No answer')[:300]}\n"
        qa_summary += f"Score: {q.get('score', 0)}/10\n"

    prompt = f"""You are a senior career coach analyzing a mock interview performance in detail.

Role: {job_role} at {company}

Interview Summary:
{qa_summary}

Provide a COMPREHENSIVE assessment as a JSON object with ALL these fields:
- "overall_score": average score out of 10 (number)
- "rating": one of "Excellent", "Good", "Average", "Needs Improvement", "Poor"
- "overall_feedback": 3-4 sentence summary of performance
- "technical_score": score for technical questions out of 10 (number, 0 if no technical questions)
- "hr_score": score for HR/behavioral questions out of 10 (number, 0 if no HR questions)
- "communication_score": rating of communication clarity out of 10 (number)
- "confidence_score": how confident the answers appear out of 10 (number)
- "top_strengths": array of 3 key strengths
- "key_weaknesses": array of 3 areas to improve
- "action_items": array of 3 specific suggestions for improvement
- "skill_gaps": array of 3-5 objects, each with:
    - "skill": name of the skill that needs improvement
    - "current_level": "Beginner", "Intermediate", or "Advanced"
    - "target_level": where they should be
    - "priority": "High", "Medium", or "Low"
- "learning_resources": array of 5 objects, each with:
    - "topic": what to study
    - "description": 1-2 sentence description of what to learn
    - "resource_type": one of "Course", "Book", "Practice", "Video", "Article"
    - "platform": suggested platform like "YouTube", "Udemy", "LeetCode", "GeeksforGeeks", "Coursera", "InterviewBit", etc.
- "improvement_roadmap": array of 3 objects, each with:
    - "week": "Week 1", "Week 2", "Week 3"
    - "focus": main focus area for that week
    - "tasks": array of 2-3 specific tasks to do that week
- "weak_question_types": array of question categories/topics the candidate struggled with most
- "strong_question_types": array of question categories/topics the candidate did well on

Return ONLY the JSON object, no other text."""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            # Ensure all required fields exist
            result.setdefault('technical_score', 0)
            result.setdefault('hr_score', 0)
            result.setdefault('communication_score', 5)
            result.setdefault('confidence_score', 5)
            result.setdefault('skill_gaps', [])
            result.setdefault('learning_resources', [])
            result.setdefault('improvement_roadmap', [])
            result.setdefault('weak_question_types', [])
            result.setdefault('strong_question_types', [])
            return result
        else:
            return _fallback_overall(questions_data)
    except Exception as e:
        print(f"AI Overall Feedback Error: {e}")
        return _fallback_overall(questions_data)


def _fallback_questions(job_role, interview_type, num_questions):
    """Fallback questions if AI fails."""
    technical = [
        {"question": f"What are the key skills required for a {job_role}?", "category": "Technical", "difficulty": "Easy"},
        {"question": "Explain a complex project you've worked on recently.", "category": "Technical", "difficulty": "Medium"},
        {"question": "How do you approach debugging a critical production issue?", "category": "Technical", "difficulty": "Hard"},
        {"question": "What design patterns are you most familiar with?", "category": "Technical", "difficulty": "Medium"},
        {"question": "How do you ensure code quality in your projects?", "category": "Technical", "difficulty": "Medium"},
        {"question": "Describe how you would optimize the performance of a slow-running application.", "category": "Technical", "difficulty": "Hard"},
        {"question": "How do you stay updated with the latest trends in technology?", "category": "Technical", "difficulty": "Easy"},
        {"question": "Explain the concept of continuous integration and continuous deployment (CI/CD).", "category": "Technical", "difficulty": "Medium"},
        {"question": "Can you explain the differences between REST and GraphQL?", "category": "Technical", "difficulty": "Medium"},
        {"question": "Give an example of a time when you optimized a poorly written piece of code.", "category": "Technical", "difficulty": "Hard"},
        {"question": "How do you handle security vulnerabilities in an application?", "category": "Technical", "difficulty": "Hard"},
        {"question": "What is unit testing and why is it important?", "category": "Technical", "difficulty": "Easy"},
        {"question": "How do you handle version control and resolving conflicts in Git?", "category": "Technical", "difficulty": "Medium"},
        {"question": "Describe a system architecture you have built or worked on.", "category": "Technical", "difficulty": "Hard"},
        {"question": "How do you structure your code to ensure scalability and maintainability?", "category": "Technical", "difficulty": "Medium"},
    ]
    hr = [
        {"question": "Tell me about yourself.", "category": "HR/Behavioral", "difficulty": "Easy"},
        {"question": "Why do you want to work at this company?", "category": "HR/Behavioral", "difficulty": "Easy"},
        {"question": "Describe a challenging situation and how you handled it.", "category": "HR/Behavioral", "difficulty": "Medium"},
        {"question": "Where do you see yourself in 5 years?", "category": "HR/Behavioral", "difficulty": "Easy"},
        {"question": "How do you handle disagreements with team members?", "category": "HR/Behavioral", "difficulty": "Medium"},
        {"question": "Give an example of a time you demonstrated leadership skills.", "category": "HR/Behavioral", "difficulty": "Medium"},
        {"question": "Describe a time you failed and what you learned from it.", "category": "HR/Behavioral", "difficulty": "Medium"},
        {"question": "What is your biggest weakness?", "category": "HR/Behavioral", "difficulty": "Easy"},
        {"question": "How do you prioritize your work when dealing with tight deadlines?", "category": "HR/Behavioral", "difficulty": "Medium"},
        {"question": "Tell me about a time you had to adapt to a sudden change in scope.", "category": "HR/Behavioral", "difficulty": "Hard"},
        {"question": "How do you motivate yourself in a remote work environment?", "category": "HR/Behavioral", "difficulty": "Easy"},
        {"question": "Describe a time when you received constructive criticism. How did you handle it?", "category": "HR/Behavioral", "difficulty": "Medium"},
        {"question": "What motivates you in your professional life?", "category": "HR/Behavioral", "difficulty": "Easy"},
        {"question": "Tell me about a time you went above and beyond the call of duty.", "category": "HR/Behavioral", "difficulty": "Hard"},
        {"question": "How do you manage stress in high-pressure situations?", "category": "HR/Behavioral", "difficulty": "Medium"},
    ]

    import random
    random.shuffle(technical)
    random.shuffle(hr)

    if interview_type == "technical":
        pool = technical
    elif interview_type == "hr":
        pool = hr
    else:
        # Mix them up
        pool = technical[:num_questions//2 + 1] + hr[:num_questions//2 + 1]
        random.shuffle(pool)

    # In case num_questions exceeds pool size, only then we might repeat (but it shouldn't, max is 20)
    if len(pool) < num_questions:
        pool = pool * ((num_questions // len(pool)) + 1)
        
    return pool[:num_questions]


def _fallback_evaluation(user_answer):
    word_count = len(user_answer.split())
    if word_count > 50:
        score = 6
        feedback = "Your answer shows some depth. Consider adding more specific examples."
    elif word_count > 20:
        score = 5
        feedback = "Decent attempt. Try to elaborate more with concrete examples."
    else:
        score = 3
        feedback = "Your answer is too brief. Provide more detailed explanations."

    return {
        "score": score,
        "feedback": feedback,
        "strengths": ["Attempted the question"],
        "improvements": ["Add more detail", "Use specific examples"]
    }


def _fallback_overall(questions_data):
    scores = [q.get('score', 0) for q in questions_data]
    avg = sum(scores) / len(scores) if scores else 0

    tech_scores = [q.get('score', 0) for q in questions_data if 'Technical' in q.get('category', '')]
    hr_scores = [q.get('score', 0) for q in questions_data if 'HR' in q.get('category', '') or 'Behavioral' in q.get('category', '')]
    tech_avg = round(sum(tech_scores) / len(tech_scores), 1) if tech_scores else 0
    hr_avg = round(sum(hr_scores) / len(hr_scores), 1) if hr_scores else 0

    if avg >= 8: rating = "Excellent"
    elif avg >= 6: rating = "Good"
    elif avg >= 4: rating = "Average"
    elif avg >= 2: rating = "Needs Improvement"
    else: rating = "Poor"

    return {
        "overall_score": round(avg, 1),
        "rating": rating,
        "overall_feedback": f"You scored an average of {round(avg, 1)}/10 across all questions.",
        "technical_score": tech_avg,
        "hr_score": hr_avg,
        "communication_score": min(round(avg + 1, 1), 10),
        "confidence_score": min(round(avg + 0.5, 1), 10),
        "top_strengths": ["Completed the interview", "Showed willingness to learn", "Attempted all questions"],
        "key_weaknesses": ["Need more detailed answers", "Add specific examples", "Structure answers better"],
        "action_items": ["Practice answering with STAR method", "Research the company thoroughly", "Prepare technical fundamentals"],
        "skill_gaps": [
            {"skill": "Communication", "current_level": "Beginner", "target_level": "Intermediate", "priority": "High"},
            {"skill": "Technical Knowledge", "current_level": "Beginner", "target_level": "Intermediate", "priority": "High"},
            {"skill": "Problem Solving", "current_level": "Beginner", "target_level": "Intermediate", "priority": "Medium"}
        ],
        "learning_resources": [
            {"topic": "STAR Interview Method", "description": "Learn how to structure your behavioral answers using Situation, Task, Action, Result format.", "resource_type": "Video", "platform": "YouTube"},
            {"topic": "Technical Interview Prep", "description": "Practice common coding and system design problems.", "resource_type": "Practice", "platform": "LeetCode"},
            {"topic": "Communication Skills", "description": "Improve your professional communication for interviews.", "resource_type": "Course", "platform": "Coursera"},
            {"topic": "Company Research", "description": "Learn how to research companies before interviews.", "resource_type": "Article", "platform": "Glassdoor"},
            {"topic": "Mock Interview Practice", "description": "Practice with more mock interviews to build confidence.", "resource_type": "Practice", "platform": "InterviewBit"}
        ],
        "improvement_roadmap": [
            {"week": "Week 1", "focus": "Foundation Building", "tasks": ["Study STAR method for behavioral questions", "Review core technical concepts", "Research target companies"]},
            {"week": "Week 2", "focus": "Practice & Application", "tasks": ["Practice 5 behavioral questions daily", "Solve 3 technical problems daily", "Record yourself answering questions"]},
            {"week": "Week 3", "focus": "Mock Interviews & Refinement", "tasks": ["Take 2-3 full mock interviews", "Get feedback from peers", "Refine answers based on feedback"]}
        ],
        "weak_question_types": ["Behavioral questions", "Technical depth"],
        "strong_question_types": ["Self-introduction", "Basic concepts"]
    }
