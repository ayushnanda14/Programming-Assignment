import pandas as pd
import numpy as np
import sys

# Reading the File Name from the command line
marks_file = sys.argv[1]

# Using the pandas library to read the csv file contents
marks = pd.read_csv(marks_file)

def get_max_inds(arr):
    maxx = max(arr)
    return [ i for i in range(len(arr)) if arr[i] == maxx]


print()
for i in marks.columns[1:]:
    # For the first task we have to find the Toppers in each subject
    # Here I have used the numpy's argmax function to find the index of the student who has attained the highest marks
    
    # For printing only one topper : topper_list = get_max_inds(marks[i])[:1]

    topper_list = get_max_inds(marks[i])
    print('Topper in %s %s'%(i, 'is' if len(topper_list) == 1 else 'are'),end=" ")
    
    for j in topper_list:
        print('{}'.format(marks['Name'][j]), end=" ")
    print()

    
# For the second task we need to Top 3 students of the class

# First I have calculated the total marks of each student over all the subjects
total_marks = []
for i in range(len(marks)):
    total_marks.append(sum(marks.iloc[i,1:]))


# Then I have used the max finding method for three values 
# i.e. in general max finding procedure we take 2 variables- 1. one for keeping track of the max value 2. other for keeping track of its index
# Here I have taken 3 variables for keeping track of the three max values and another 3 variables for keeping track of their indices 

one, two, three = -1, -1, -1
onei, twoi, threei = -1, -1, -1

for i in range(len(total_marks)):
    if total_marks[i] >= one:
        three = two
        threei = twoi
        two = one
        twoi = onei
        one = total_marks[i]
        onei = i

    elif total_marks[i] >= two:
        three = two
        threei = twoi
        two = total_marks[i]
        twoi = i

    elif total_marks[i] >= three:
        three = total_marks[i]
        threei = i

print('\nBest students in the class are {}, {}, {}\n'.format(marks['Name'][onei], marks['Name'][twoi], marks['Name'][threei]))

'''
    The first task has a Time Complexity of O(n*S) and Space Complexity of O(1)
    - where n = number of students in the marklist 
    - and   S = number of subjects
    which means that finding the topper of each subject has a Time Complexity of O(n) 

    The second task has a time complexity of O(n*S + n) which is equal to O(n*S) and Space Complexity of O(n)
'''

