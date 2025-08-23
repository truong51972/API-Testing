from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import UserProject
from testcase_history.models import TestCaseHistory
from test_suite.models import ProjectTestSuite
from main.decorators import set_test_suites_show

@set_test_suites_show(True)
@login_required
def test_suite_add(request, project_uuid):
    # Retrieve the project by UUID or raise a 404 error if not found
    project = get_object_or_404(UserProject, uuid=project_uuid)
    test_suites = ProjectTestSuite.objects.filter(project=project)

    context = {
        'project': project,
        'test_suites': test_suites,
    }

    if project.user != request.user:
        messages.error(request, "You do not have permission to add a test suite to this project.")
        return redirect('project_list')

    if request.method == 'POST':
        # Handle form submission for adding a test suite
        test_suite_name = request.POST.get('test_suite_name')
        description = request.POST.get('description', '')

        # Create a new test suite instance and save it to the database
        if not test_suite_name:
            messages.error(request, "Test suite name is required.")
            return render(request, 'test_suite/test_suite_add.html', context)
        
        if ProjectTestSuite.objects.filter(project=project, test_suite_name=test_suite_name).exists():
            messages.error(request, "Test suite with this name already exists in this project.")
            return render(request, 'test_suite/test_suite_add.html', context)
        
        test_suite = ProjectTestSuite(project=project, test_suite_name=test_suite_name, description=description)
        test_suite.save()
        messages.success(request, "Test suite added successfully.")
        return redirect(reverse('test_suite_detail', kwargs={'test_suite_uuid': test_suite.uuid}))
    else:
        # Render the test suite add form
        return render(request, 'test_suite/test_suite_add.html', context)

@set_test_suites_show(True)
@login_required
def test_suite_detail(request, test_suite_uuid):
    # Retrieve the test suite by UUID or raise a 404 error if not found

    test_suite = get_object_or_404(ProjectTestSuite, uuid=test_suite_uuid)
    project_test_suites = ProjectTestSuite.objects.filter(project=test_suite.project)

    if test_suite.project.user != request.user:
        messages.error(request, "You do not have permission to view this test suite.")
        return redirect('project_list')
        
    # Fetch related test cases from TestCaseHistory
    test_cases = TestCaseHistory.objects.filter(test_suite=test_suite)

    context = {
        'project': test_suite.project,
        'test_suites': project_test_suites,
        'test_suite': test_suite,
        'test_cases': test_cases,
    }
    
    return render(request, 'test_suite/test_suite_detail.html', context)

# Create your views here.
