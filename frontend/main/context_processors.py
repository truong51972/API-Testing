from project.models import UserProject
from test_suite.models import ProjectTestSuite

def recent_projects(request):
    if request.user.is_authenticated:
        projects = UserProject.objects.filter(user=request.user).order_by('-created_at')[:9]
        return {'recent_projects': projects}
    return {'recent_projects': []}

def test_suites_show(request):
    return {'test_suites_show': getattr(request, '_test_suites_show', False)}