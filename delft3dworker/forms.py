from django import forms

from models import GroupUsageSummary

class GroupUsageSummaryForm(forms.ModelForm):

    class Meta:
        model = GroupUsageSummary
        fields = ('start_date', 'end_date',)