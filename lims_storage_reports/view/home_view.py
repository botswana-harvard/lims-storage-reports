from django.views.generic.base import TemplateView
from storage_module.forms import AdvancedSamplesFilterForm
from storage_module.models import *
from django.db.models import Count,Q,F
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict

class HomeView(TemplateView):
    template_name = 'lims_storage_reports/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        advanced_filter_form = AdvancedSamplesFilterForm(self.request.GET)
        filter_submitted = any(value for key, value in self.request.GET.items() if key != 'page')

        total_samples = DimSample.objects.count()

        recent_date = timezone.now() - timedelta(days=30)

        recent_samples = DimSample.objects.filter(date_sampled__gte=recent_date).count()

        queryset = self.get_queryset()
        sample_counts_table, sample_types = self.get_sample_counts_by_visit(queryset)

        context.update(
            total_samples = total_samples,
            sample_by_type = self.samples_by_type(queryset),
            recent_samples = recent_samples,
            samples_types_by_gender = self.sample_types_by_gender(queryset),
            samples_by_facility =self.samples_by_facility(queryset),
            advanced_filter_form = advanced_filter_form,
            samples_visit_count = sample_counts_table,
            sample_types_visits = sample_types,
            filter_submitted=filter_submitted

        )
        return context
    
    def samples_by_type(self, queryset):
        samples_by_type_qs = queryset.values('sample_type__sample_type').annotate(count=Count('id'))

        samples_by_type = [
            (item['sample_type__sample_type'], item['count'])
            for item in samples_by_type_qs
        ]
        return samples_by_type
    
    def sample_types_by_gender(self, queryset):
        sample_types_by_gender = list(queryset.values('sample_type__sample_type').annotate(
            count_male=Count('id', filter=Q(gender='M')),
            count_female=Count('id', filter=Q(gender='F')),
            total_count=Count('id')
        ))
        return sample_types_by_gender
    
    def samples_by_facility(self, queryset):
        samples_by_facility_qs = queryset.values(
        'box_position__box__freezer__facility__facility_name'
        ).annotate(
            sample_count=Count('id')
        ).order_by('-sample_count')
        return list(samples_by_facility_qs)
    
    def apply_advanced_filters(self, queryset, advanced_filter_form):
        """Apply filters from the advanced filter form to the queryset."""
        dob_start = advanced_filter_form.cleaned_data.get('date_of_birth_start')
        dob_end = advanced_filter_form.cleaned_data.get('date_of_birth_end')

        if dob_start and dob_end:
            queryset = queryset.filter(date_of_birth__range=(dob_start, dob_end))
        elif dob_start:
            queryset = queryset.filter(date_of_birth=dob_start)

        date_sampled_start = advanced_filter_form.cleaned_data.get('date_sampled_start')
        date_sampled_end = advanced_filter_form.cleaned_data.get('date_sampled_end')

        if date_sampled_start and date_sampled_end:
            queryset = queryset.filter(date_sampled__range=(date_sampled_start, date_sampled_end))
        elif date_sampled_start:
            queryset = queryset.filter(date_sampled=date_sampled_start)
        

        # Apply other filters
        for field in advanced_filter_form:
            if field.value() and field.name not in ['date_of_birth_start', 'date_of_birth_end', 'date_sampled_start', 'date_sampled_end']:
                queryset = queryset.filter(**{field.name: field.value()})

        return queryset
    

    def get_queryset(self):
        queryset = DimSample.objects.all()  # Display all samples by default
        # Check if advanced filter form is submitted
        advanced_filter_form = AdvancedSamplesFilterForm(self.request.GET)
        if advanced_filter_form.is_valid():
            # Apply filters if form is valid
            queryset = self.apply_advanced_filters(queryset, advanced_filter_form)

        search_value = self.request.GET.get('search_value', None)
        if search_value:
            # Adjust fields to match the columns you want to search in
            queryset = queryset.filter(
                Q(sample_id__icontains=search_value) |
                Q(sample_type__sample_type__icontains=search_value)|
                Q(protocol_number__icontains=search_value)
                )

        return queryset
    
    def get_sample_counts_by_visit(self,queryset):
        # Query to group by visit_code and sample_type, counting each sample
        query_results = queryset.values('visit_code', 'sample_type__sample_type').annotate(count=Count('id'),
                                                                                           distinct_count=Count('participant_id', distinct=True))

        # Initialize a structure to organize data for easy table rendering
        sample_counts = defaultdict(lambda: defaultdict(int))
        sample_types = set()

        # Populate the data structure
        for result in query_results:
            visit_code = result['visit_code']
            sample_type = result['sample_type__sample_type'] or "Unknown Type"
            count = result['count']
            distinct_count = result['distinct_count']

            sample_counts[visit_code][sample_type] = {
                'total_count':count,
                'distinct_count':distinct_count,
                }

            sample_types.add(sample_type)

        # Convert sample_types to a sorted list for column consistency in templates
        sample_types = sorted(sample_types)

        # Convert the nested dictionary to a list of dictionaries for the template
        sample_counts_table = []
        for visit_code, counts in sample_counts.items():
            row = {'visit_code': visit_code}
            for sample_type in sample_types:
                row[f'{sample_type}_total'] = counts.get(sample_type, {}).get('total_count', 0)
                row[f'{sample_type}_distinct'] = counts.get(sample_type, {}).get('distinct_count', 0)
            sample_counts_table.append(row)

        return  sample_counts_table, sample_types     # List of all sample types (for table columns)
            
    

    
    
    
    

    
