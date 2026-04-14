// src/app/services/dynamic-title.service.ts
import { Injectable } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { UniversityThemeService } from './university-theme.service';

@Injectable({
  providedIn: 'root'
})
export class DynamicTitleService {
  constructor(
    private titleService: Title,
    private themeService: UniversityThemeService
  ) {}

  updateTitleForUniversity(universityXId: string) {
    this.themeService.loadUniversityBranding(universityXId).subscribe({
      next: (branding) => {
        const universityName = branding.university.name;
        this.titleService.setTitle(`${universityName} - AI Assistant`);
      },
      error: () => {
        this.titleService.setTitle('University AI Assistant');
      }
    });
  }
}