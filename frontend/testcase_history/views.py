from django.shortcuts import render
from django.views import View
from django.contrib.auth.decorators import login_required

@login_required
def testcase_history(request):
    # This view will render the test case history page
    return render(request, 'testcase_history/testcase_history.html')


    
