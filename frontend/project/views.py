from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from .models import UserProject
from testcase_history.models import TestCaseHistory
from test_suite.models import ProjectTestSuite
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from main.decorators import set_test_suites_show
from .forms import ProjectDocumentForm  
from .models import ProjectDocument    

@login_required
def project_list(request):
    # This view will render the list of projects for the logged-in user
    projects = UserProject.objects.filter(user=request.user)
    if not projects:
        messages.info(request, "You have no projects yet. Consider adding one.")
    # You can also paginate the projects if needed
    # For example, using Django's built-in pagination:
    # Optionally, you can also fetch related data like test cases or test suites if needed
    # For example, to get test cases related to the projects:

    context = {
        'projects': [{
            'uuid': project.uuid,
            'project_name': project.project_name,
            'description': project.description,
            'created_at': project.created_at,
            'test_suites_count_per_project': ProjectTestSuite.objects.filter(project=project).count(),
            'test_cases_count_per_project': TestCaseHistory.objects.filter(test_suite__project=project).count()
        } for project in projects]
    }
    return render(request, 'project/project_list.html', context)

@login_required
def project_add(request):
    # This view will handle adding a new project
    if request.method == 'POST':
        # Handle form submission for adding a project
        project_name = request.POST.get('project_name')
        description = request.POST.get('description', '')
        user = request.user

        # Create a new project instance and save it to the database
        if not project_name:
            messages.error(request, "Project name is required.")
            return render(request, 'project/project_add.html')
        
        if UserProject.objects.filter(user=user, project_name=project_name).exists():
            messages.error(request, "Project with this name already exists.")
            return render(request, 'project/project_add.html')
        
        project = UserProject(user=user, project_name=project_name, description=description)
        project.save()
        messages.success(request, "Project added successfully.")
        return redirect(reverse('project_detail_by_uuid', kwargs={'project_uuid': project.uuid}))
    else:
        # Render the project add form
        return render(request, 'project/project_add.html')

@set_test_suites_show(True)
@login_required
def project_detail_by_uuid(request, project_uuid):
    # Use get_object_or_404 to retrieve the object or raise a 404 error if not found
    project = get_object_or_404(UserProject, uuid=project_uuid)
    if project.user != request.user:
        messages.error(request, "You do not have permission to view this project.")
        return redirect('project_list')
    test_suites = ProjectTestSuite.objects.filter(project=project)


    context = {
        'project': project,
        'test_suites': [{
            'uuid': test_suite.uuid,
            'test_suite_name': test_suite.test_suite_name,
            'description': test_suite.description,
            'created_at': test_suite.created_at,
            'test_cases_count': TestCaseHistory.objects.filter(test_suite=test_suite).count()
        } for test_suite in test_suites],
    }
    return render(request, 'project/project_view.html', context)

@set_test_suites_show(True)
@login_required
def project_edit(request, project_uuid):
    # This view will handle editing an existing project
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    if project.user != request.user:
        messages.error(request, "You do not have permission to edit this project.")
        return redirect('project_list')
    
    test_suites = ProjectTestSuite.objects.filter(project=project)

    context = {
        'project': project,
        'test_suites': test_suites,
    }


    if request.method == 'POST':
        project_name = request.POST.get('project_name')
        description = request.POST.get('description', '')

        if not project_name:
            messages.error(request, "Project name is required.")
            return render(request, 'project/project_edit.html', context)

        # Update the project instance and save it to the database
        project.project_name = project_name
        project.description = description
        project.save()
        messages.success(request, "Project updated successfully.")
        return redirect(reverse('project_detail_by_uuid', kwargs={'project_uuid': project.uuid}))
    
    return render(request, 'project/project_edit.html', context)

@set_test_suites_show(True)
@login_required
def project_delete(request, project_uuid):
    # This view will handle deleting an existing project
    project = get_object_or_404(UserProject, uuid=project_uuid, user=request.user)
    if project.user != request.user:
        messages.error(request, "You do not have permission to delete this project.")
        return redirect('project_list')
    test_suites = ProjectTestSuite.objects.filter(project=project)
    context = {
        'project': project,
        'test_suites': test_suites,
    }
    
    if request.method == 'POST':
        project.delete()
        messages.success(request, "Project deleted successfully.")
        return redirect('project_list')
    return render(request, 'project/project_delete.html', context)

@set_test_suites_show(True)
@login_required
def project_detail_by_uuid(request, project_uuid):
    project = get_object_or_404(UserProject, uuid=project_uuid)
    if project.user != request.user:
        messages.error(request, "You do not have permission to view this project.")
        return redirect('project_list')

    test_suites = ProjectTestSuite.objects.filter(project=project)

    # Lấy list tài liệu đã upload
    documents = project.documents.all() if hasattr(project, "documents") else []

    # Xử lý form upload
    if request.method == "POST":
        form = ProjectDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.project = project
            doc.save()
            messages.success(request, "Tài liệu đã được thêm thành công.")
            return redirect(reverse('project_detail_by_uuid', kwargs={'project_uuid': project.uuid}))
        else:
            messages.error(request, "Có lỗi khi upload/nhập tài liệu.")
    else:
        form = ProjectDocumentForm()

    context = {
        'project': project,
        'test_suites': [{
            'uuid': test_suite.uuid,
            'test_suite_name': test_suite.test_suite_name,
            'description': test_suite.description,
            'created_at': test_suite.created_at,
            'test_cases_count': TestCaseHistory.objects.filter(test_suite=test_suite).count()
        } for test_suite in test_suites],
        'form': form,
        'documents': documents,
    }
    return render(request, 'project/project_view.html', context)

@set_test_suites_show(True)
@login_required
def delete_document(request, doc_id):
    doc = get_object_or_404(ProjectDocument, id=doc_id, project__user=request.user)
    project_uuid = doc.project.uuid
    doc.delete()
    messages.success(request, "Tài liệu đã được xoá.")
    return redirect(reverse('project_detail_by_uuid', kwargs={'project_uuid': project_uuid}))
