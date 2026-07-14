from django import forms
from accounts.models import Societe, User as Utilisateur
from .models import Entreprise
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

class SocieteForm(forms.ModelForm):

    class Meta:
        model = Societe
        fields = ('nom',)
        
class EntrepriseForm(forms.ModelForm):
    class Meta:
        model = Entreprise
        fields = ['nom', 'adresse', 'secteur_activite', 'telephone', 'email', 'is_CLT', 'is_Prospect', 'is_Concurent', 'societe', 'date', 'num_compte']

class EntrepriseFormEdit(forms.ModelForm):
    class Meta:
        model = Entreprise
        fields = ['nom', 'adresse', 'secteur_activite', 'telephone', 'email', 'date', 'num_compte']
        
class UtilisateurCreationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[('C', 'Commercial'), ('RC', 'Responsable Commercial')],
        widget=forms.RadioSelect,
        required=True,
        label="Rôle"
    )
    class Meta:
        model = Utilisateur
        fields = ('username', 'email', 'is_C', 'is_RC', 'societe', 'telephone', 'role')

class UtilisateurChangeForm(UserChangeForm):
    class Meta:
        model = Utilisateur
        fields = ('username', 'email', 'is_C', 'is_RC', 'societe', 'telephone')