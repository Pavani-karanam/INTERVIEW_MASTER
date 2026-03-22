import json
import os

datasets = {
    'arrays': [
        {'question': 'Find the maximum subarray sum (Kadane\'s Algorithm)', 'difficulty': 'Medium', 'category': 'Technical'},
        {'question': 'Given an array, rotate it by k elements', 'difficulty': 'Easy', 'category': 'Technical'},
        {'question': 'Two Sum - Find indices of two numbers that add up to target', 'difficulty': 'Easy', 'category': 'Technical'},
        {'question': 'Merge two sorted arrays without extra space', 'difficulty': 'Hard', 'category': 'Technical'}
    ],
    'strings': [
        {'question': 'Check if a string is a palindrome', 'difficulty': 'Easy', 'category': 'Technical'},
        {'question': 'Find the longest substring without repeating characters', 'difficulty': 'Medium', 'category': 'Technical'},
        {'question': 'Check if two strings are anagrams of each other', 'difficulty': 'Easy', 'category': 'Technical'},
        {'question': 'Implement string compression, e.g., aabbbcccc -> a2b3c4', 'difficulty': 'Medium', 'category': 'Technical'}
    ],
    'dp': [
        {'question': 'Fibonacci Number using Memoization and Tabulation', 'difficulty': 'Easy', 'category': 'Technical'},
        {'question': 'Longest Common Subsequence (LCS)', 'difficulty': 'Medium', 'category': 'Technical'},
        {'question': '0/1 Knapsack Problem', 'difficulty': 'Medium', 'category': 'Technical'},
        {'question': 'Edit Distance (Levenshtein distance) between two strings', 'difficulty': 'Hard', 'category': 'Technical'}
    ],
    'trees': [
        {'question': 'Inorder, Preorder, and Postorder Traversals', 'difficulty': 'Easy', 'category': 'Technical'},
        {'question': 'Find the maximum depth of a binary tree', 'difficulty': 'Easy', 'category': 'Technical'},
        {'question': 'Lowest Common Ancestor (LCA) of a binary tree', 'difficulty': 'Medium', 'category': 'Technical'},
        {'question': 'Serialize and Deserialize a Binary Tree', 'difficulty': 'Hard', 'category': 'Technical'}
    ],
    'graphs': [
        {'question': 'Implement Breadth First Search (BFS)', 'difficulty': 'Medium', 'category': 'Technical'},
        {'question': 'Implement Depth First Search (DFS)', 'difficulty': 'Medium', 'category': 'Technical'},
        {'question': 'Find shortest path using Dijkstra\'s Algorithm', 'difficulty': 'Hard', 'category': 'Technical'},
        {'question': 'Detect a cycle in a directed graph', 'difficulty': 'Medium', 'category': 'Technical'}
    ],
    'sorting': [
        {'question': 'Implement Merge Sort', 'difficulty': 'Medium', 'category': 'Technical'},
        {'question': 'Implement Quick Sort', 'difficulty': 'Medium', 'category': 'Technical'},
        {'question': 'Find the Kth largest element in an array', 'difficulty': 'Medium', 'category': 'Technical'},
        {'question': 'Sort an array of 0s, 1s, and 2s (Dutch National Flag problem)', 'difficulty': 'Medium', 'category': 'Technical'}
    ],
    'sql': [
        {'question': 'Find the nth highest salary from an Employee table', 'difficulty': 'Medium', 'category': 'Technical'},
        {'question': 'Write a query to find duplicates in a table', 'difficulty': 'Easy', 'category': 'Technical'},
        {'question': 'Inner Join vs Left Join vs Right Join', 'difficulty': 'Easy', 'category': 'Technical'},
        {'question': 'Optimize a slow-running complex SQL query', 'difficulty': 'Hard', 'category': 'Technical'}
    ],
    'system_design': [
        {'question': 'Design a URL shortener like TinyURL', 'difficulty': 'Medium', 'category': 'Technical'},
        {'question': 'Design an instant messaging app like WhatsApp', 'difficulty': 'Hard', 'category': 'Technical'},
        {'question': 'Design Netflix or a video streaming service', 'difficulty': 'Hard', 'category': 'Technical'},
        {'question': 'How do you structure microservices communication?', 'difficulty': 'Medium', 'category': 'Technical'}
    ],
    'oop': [
        {'question': 'Explain Encapsulation, Abstraction, Inheritance, and Polymorphism', 'difficulty': 'Easy', 'category': 'Technical'},
        {'question': 'Difference between Interface and Abstract Class', 'difficulty': 'Easy', 'category': 'Technical'},
        {'question': 'What is Method Overloading vs Method Overriding?', 'difficulty': 'Medium', 'category': 'Technical'},
        {'question': 'Design a generic Object-Oriented Parking Lot System', 'difficulty': 'Hard', 'category': 'Technical'}
    ],
    'react': [
        {'question': 'What is the Virtual DOM in React and why is it fast?', 'difficulty': 'Medium', 'category': 'Technical'},
        {'question': 'Explain the useEffect hook lifecycle', 'difficulty': 'Medium', 'category': 'Technical'},
        {'question': 'How do you pass data between sibling components?', 'difficulty': 'Easy', 'category': 'Technical'},
        {'question': 'What is React Context API and when should you use it over Redux?', 'difficulty': 'Medium', 'category': 'Technical'}
    ],
    'python': [
        {'question': 'What are decorators and how do you write a custom one?', 'difficulty': 'Medium', 'category': 'Technical'},
        {'question': 'List comprehension vs map/filter functions', 'difficulty': 'Easy', 'category': 'Technical'},
        {'question': 'Explain Global Interpreter Lock (GIL) and its impact on threading', 'difficulty': 'Hard', 'category': 'Technical'},
        {'question': 'Difference between *args and **kwargs', 'difficulty': 'Easy', 'category': 'Technical'}
    ],
    'behavioral': [
        {'question': 'Tell me about a time you had a conflict with a colleague.', 'difficulty': 'Medium', 'category': 'HR/Behavioral'},
        {'question': 'Describe a project that failed and what you learned from it.', 'difficulty': 'Medium', 'category': 'HR/Behavioral'},
        {'question': 'Where do you see yourself in 5 years?', 'difficulty': 'Easy', 'category': 'HR/Behavioral'},
        {'question': 'Why should we hire you over other candidates?', 'difficulty': 'Medium', 'category': 'HR/Behavioral'}
    ]
}

os.makedirs('datasets', exist_ok=True)
for key, value in datasets.items():
    with open(f'datasets/{key}.json', 'w', encoding='utf-8') as f:
        json.dump(value, f, indent=4)
