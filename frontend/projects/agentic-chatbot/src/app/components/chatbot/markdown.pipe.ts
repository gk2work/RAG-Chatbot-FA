import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

@Pipe({
  name: 'markdown',
  standalone: true
})
export class MarkdownPipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}

  transform(value: string): SafeHtml {
    if (!value) return '';

    let html = value;
    
    // Convert markdown headers with optional leading spaces and emoji prefixes
    const leading = '[\\s\u00A0\u200B\uFEFF]*';
    const emojiPrefix = '(?:[🎓⏱️📋💰💡])?\\s*';
    const h3Pattern = new RegExp('^' + leading + '(?:' + emojiPrefix + ')?###\\s*(.+)$', 'gmu');
    const h2Pattern = new RegExp('^' + leading + '(?:' + emojiPrefix + ')?##\\s*(.+)$', 'gmu');
    const h1Pattern = new RegExp('^' + leading + '(?:' + emojiPrefix + ')?#\\s*(.+)$', 'gmu');
    html = html.replace(h3Pattern, '<h3 class="markdown-h3">$1</h3>');
    html = html.replace(h2Pattern, '<h2 class="markdown-h2">$1</h2>');
    html = html.replace(h1Pattern, '<h1 class="markdown-h1">$1</h1>');
    
    // Convert **text** to <strong>text</strong>
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="highlight-text">$1</strong>');
    
    // Convert *text* to <em>text</em> (italics)
    html = html.replace(/\*([^*]+)\*/g, '<em class="italic-text">$1</em>');
    
    // Highlight program names (like MBA, BBA, etc.) - more comprehensive
    html = html.replace(/\b(MBA|BBA|PhD|MSc|BSc|DBA|Executive|Master|Bachelor|Diploma|Certificate|Programs?|Courses?)\b/gi, '<span class="program-highlight">$1</span>');
    
    // Convert numbered lists with better formatting (remove extra line breaks)
    html = html.replace(/^(\d+)\.\s+(.+)$/gm, '<div class="numbered-item"><span class="number-badge">$1</span> <span class="item-content">$2</span></div>');
    
    // Highlight course/program titles in parentheses
    html = html.replace(/\(([A-Z]{2,})\)/g, '(<span class="course-code">$1</span>)');
    
    // Convert bullet points
    html = html.replace(/^[-*]\s+(.+)$/gm, '<div class="bullet-item">• $1</div>');
    
    // Handle horizontal rules/dividers
    html = html.replace(/^---+$/gm, '<hr class="markdown-divider">');

    // Normalize line endings and excess whitespace before converting to <br>
    html = html.replace(/\r\n?/g, '\n');
    // Trim trailing spaces on each line
    html = html.replace(/[ \t\u00A0\u200B\uFEFF]+$/gmu, '');
    // Collapse 3+ blank lines down to 2
    html = html.replace(/\n{3,}/g, '\n\n');

    // Fallback BEFORE <br> conversion: strip any remaining header markers at line starts
    const strayHeader = new RegExp('^' + leading + '(?:' + emojiPrefix + ')?#{1,6}[\s\u00A0\u200B\uFEFF]*', 'gmu');
    html = html.replace(strayHeader, '');

    // Only convert standalone line breaks (not those already in structured content)
    html = html.replace(/\n(?!<div|<h[1-6]|<hr)/g, '<br>');
    // Reduce excessive vertical spacing
    html = html.replace(/(?:<br>\s*){3,}/g, '<br><br>');
    // Remove leading/trailing <br>
    html = html.replace(/^(?:<br>\s*)+/, '');
    html = html.replace(/(?:<br>\s*)+$/, '');

    // Final trim
    html = html.trim();
    
    return this.sanitizer.bypassSecurityTrustHtml(html);
  }
}