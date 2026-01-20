from django.shortcuts import render
from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Count, Avg, F, Q
from django.http import HttpResponse
import csv
import datetime

# Import models
from visit_regn.models import Visit
from filing.models import OfficeFile
from accounts.models import User, Desk
from routing.models import DeskQueue

class MISDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'mis/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate consistent start/end of day
        today = timezone.localtime().date()
        start_of_day = timezone.make_aware(datetime.datetime.combine(today, datetime.time.min))
        end_of_day = timezone.make_aware(datetime.datetime.combine(today, datetime.time.max))
        
        # KPI 1: Visits Today
        context['visits_today'] = Visit.objects.filter(
            token_issue_time__range=(start_of_day, end_of_day)
        ).count()
        
        # KPI 2: Active Tokens (Waiting or In Progress - not Completed/Cancelled)
        context['active_tokens'] = Visit.objects.filter(
            token_issue_time__range=(start_of_day, end_of_day),
            status__in=['WAITING', 'ROUTED', 'IN_PROGRESS']
        ).count()
        
        # KPI 3: Pending Office Files (Total Open)
        context['pending_files'] = OfficeFile.objects.filter(
            status='OPEN'
        ).count()

        # KPI 3.5: Closed Office Files
        context['closed_files'] = OfficeFile.objects.filter(
            status='CLOSED'
        ).count()
        
        # KPI 4: Average Wait Time (Approximate - Difference between Issue and Attend time)
        # Only for those attended today
        visited_today = Visit.objects.filter(
            token_issue_time__range=(start_of_day, end_of_day),
            token_attend_time__isnull=False
        )
        avg_wait = visited_today.aggregate(
            avg_diff=Avg(F('token_attend_time') - F('token_issue_time'))
        )['avg_diff']
        
        if avg_wait:
            # Convert timedelta to minutes
            context['avg_wait_time'] = int(avg_wait.total_seconds() / 60)
        else:
            context['avg_wait_time'] = 0

        # Chart Data: Purpose Breakdown (Today)
        purpose_data = Visit.objects.filter(
            token_issue_time__range=(start_of_day, end_of_day)
        ).values(
            'purpose__name'
        ).annotate(count=Count('id')).order_by('-count')
        
        context['chart_labels'] = [item['purpose__name'] for item in purpose_data]
        context['chart_data'] = [item['count'] for item in purpose_data]

        return context

class BaseReportView(LoginRequiredMixin, ListView):
    """
    Base view for reports with date filtering and export.
    """
    paginate_by = 50
    
    def get_filter_dates(self):
        from_date = self.request.GET.get('from_date')
        to_date = self.request.GET.get('to_date')
        
        today = timezone.localtime().date()
        
        if not from_date:
            from_date = today
        else:
            from_date = datetime.datetime.strptime(from_date, '%Y-%m-%d').date()
            
        if not to_date:
            to_date = today
        else:
            to_date = datetime.datetime.strptime(to_date, '%Y-%m-%d').date()
            
        return from_date, to_date

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from_date, to_date = self.get_filter_dates()
        context['from_date'] = from_date.strftime('%Y-%m-%d')
        context['to_date'] = to_date.strftime('%Y-%m-%d')
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['report_title'] = self.report_title
        return context
    
    def render_to_response(self, context, **response_kwargs):
        # Handle Export
        if 'export' in self.request.GET:
            return self.export_csv(self.get_queryset())
        return super().render_to_response(context, **response_kwargs)

    def export_csv(self, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{self.report_title}_{timezone.now().date()}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(self.export_headers)
        
        for item in queryset:
            writer.writerow(self.get_export_row(item))
            
        return response

class DailyReportView(BaseReportView):
    model = Visit
    template_name = 'mis/report_list_final.html'
    report_title = "Daily Visit Report"
    export_headers = ['Token', 'Visitor Name', 'Purpose', 'Status', 'Issued At', 'Attended At']
    
    def get_queryset(self):
        from_date, to_date = self.get_filter_dates()
        
        # Convert to timezone-aware datetime range to avoid __date lookup issues
        start_datetime = timezone.make_aware(datetime.datetime.combine(from_date, datetime.time.min))
        end_datetime = timezone.make_aware(datetime.datetime.combine(to_date, datetime.time.max))
        
        qs = Visit.objects.filter(
            token_issue_time__range=(start_datetime, end_datetime)
        ).select_related('purpose', 'office').order_by('-token_issue_time')

        
        # Search
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(token__icontains=search))
            
        # Status Filter
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
            
        return qs
        
    def get_export_row(self, visit):
        return [
            visit.token,
            visit.name,
            visit.purpose.name,
            visit.get_status_display(),
            visit.formatted_issue_time,
            visit.token_attend_time
        ]
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Visit.Status.choices
        context['columns'] = ['Token', 'Visitor Name', 'Purpose', 'Status', 'Time']
        context['row_template'] = 'mis/partials/row_daily.html' # We will include this
        return context

class FileStatusReportView(BaseReportView):
    model = OfficeFile
    template_name = 'mis/report_list_final.html'
    report_title = "File Status Report"
    export_headers = ['File Number', 'Applicant', 'Interim Status', 'Final Status', 'Desk']
    
    def get_queryset(self):
        qs = OfficeFile.objects.all().select_related('visit', 'desk').order_by('-created_at')
        
        # Search (by file number or applicant name in linked visit)
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(
                Q(file_number__icontains=search) | 
                Q(visit__name__icontains=search)
            )
            
        # Status Filter (Final Status)
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
            
        return qs
        
    def get_export_row(self, file):
        return [
            file.file_number,
            file.visit.name if file.visit else 'N/A',
            file.get_interim_status_display(),
            file.get_status_display(),
            file.desk.name if file.desk else 'Unassigned'
        ]
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = OfficeFile.STATUS_CHOICES
        context['columns'] = ['File Number', 'Applicant', 'Interim Status', 'Status', 'Desk']
        context['row_template'] = 'mis/partials/row_files.html'
        return context


class AgingAnalysisView(BaseReportView):
    model = OfficeFile
    template_name = 'mis/report_list_final.html'
    report_title = "Aging Analysis (> 30 Days)"
    export_headers = ['File Number', 'Days Pending', 'Status', 'Desk']

    def get_queryset(self):
        # Files older than 30 days and NOT closed
        threshold_date = timezone.now() - datetime.timedelta(days=30)
        
        qs = OfficeFile.objects.filter(
            created_at__lte=threshold_date
        ).exclude(status='CLOSED').order_by('created_at')
        
        return qs

    def get_export_row(self, file):
        days = (timezone.now().date() - file.created_at.date()).days
        return [
            file.file_number,
            f"{days} days",
            file.interim_status,
            file.desk.name if file.desk else '-'
        ]
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['columns'] = ['File Number', 'Created At', 'Days Pending', 'Status', 'Desk']
        context['row_template'] = 'mis/partials/row_aging.html'
        # No date filter needed for this specific logic usually, but base class has it.
        # We can ignore it or use it to filter 'created_at' further.
        return context

class ServiceAnalysisView(LoginRequiredMixin, TemplateView):
    template_name = 'mis/service_analysis.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Aggregate visits by Purpose
        analysis = Visit.objects.values('purpose__name').annotate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='COMPLETED')),
            avg_wait=Avg(F('token_attend_time') - F('token_issue_time'))
        ).order_by('-total')
        
        context['analysis_data'] = analysis
        return context
