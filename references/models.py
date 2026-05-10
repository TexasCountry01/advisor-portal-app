from django.db import models


class ReferenceClause(models.Model):
    """
    A single verbiage clause from the Report Notes Template document.
    Technicians search and insert these into case report notes.
    """
    category = models.CharField(max_length=255, db_index=True)
    subcategory = models.CharField(max_length=500, blank=True, default='')
    title = models.CharField(max_length=500)
    body = models.TextField()
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'category', 'subcategory', 'title']
        verbose_name = 'Reference Clause'
        verbose_name_plural = 'Reference Clauses'

    def __str__(self):
        if self.subcategory:
            return f'{self.category} > {self.subcategory} > {self.title}'
        return f'{self.category} > {self.title}'
