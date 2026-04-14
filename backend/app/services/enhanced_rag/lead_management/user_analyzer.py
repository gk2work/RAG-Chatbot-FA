"""
User educational background analyzer for Enhanced RAG Service
"""

import logging
from typing import Dict, List, Any
from ..base.interfaces import BaseRAGComponent


class UserAnalyzer(BaseRAGComponent):
    """Analyzes user educational background and provides personalized insights"""
    
    def __init__(self):
        super().__init__()
        
        # Educational background detection patterns
        self.education_patterns = {
            'bachelor_level': [
                'btech', 'b.tech', 'bachelor', 'be', 'b.e', 'bs', 'b.s', 'undergraduate',
                'ug', 'bachelors', "bachelor's", 'bca', 'bcom', 'bba', 'ba', 'b.a'
            ],
            'master_level': [
                'mtech', 'm.tech', 'master', 'm.e', 'ms', 'm.s', 'mba', 'mca',
                'ma', 'm.a', 'mcom', 'postgraduate', 'pg', 'masters', "master's"
            ],
            'engineering_fields': [
                'engineering', 'tech', 'ece', 'cse', 'computer science', 'mechanical',
                'electrical', 'civil', 'chemical', 'electronics', 'it', 'information technology'
            ],
            'business_fields': [
                'business', 'management', 'mba', 'bba', 'commerce', 'finance', 'marketing'
            ]
        }
        
        # Response templates for different user types
        self.response_templates = {
            'engineering_graduate': {
                'intro_pattern': "Great to connect with a fellow engineer! With your {field} background, you're perfectly positioned for our advanced programs.",
                'focus_areas': ['technical_expertise', 'industry_applications', 'career_advancement']
            },
            'business_graduate': {
                'intro_pattern': "Excellent! With your business background in {field}, you'll find our programs align perfectly with current market demands.",
                'focus_areas': ['market_relevance', 'leadership_skills', 'professional_growth']
            },
            'fresh_graduate': {
                'intro_pattern': "Perfect timing for taking the next step in your academic journey! Our programs are designed to build upon your {field} foundation.",
                'focus_areas': ['skill_development', 'specialization', 'career_preparation']
            },
            'working_professional': {
                'intro_pattern': "As a working professional, you'll appreciate our flexible programs that complement your {field} experience.",
                'focus_areas': ['practical_applications', 'executive_development', 'work_integration']
            },
            'general': {
                'intro_pattern': "I'd be happy to help you explore our programs and find the perfect fit for your goals.",
                'focus_areas': ['program_overview', 'general_benefits', 'comprehensive_support']
            }
        }
    
    def analyze_educational_background(self, text: str) -> Dict[str, Any]:
        """Analyze user's educational background from text"""
        try:
            text_lower = text.lower()
            self.logger.debug(f"Analyzing educational background for text: '{text_lower[:100]}...'")
            
            analysis = {
                'education_level': 'unknown',
                'field_of_study': 'unknown',
                'user_type': 'general',
                'specific_degree': '',
                'progression_suggestions': []
            }
            
            # Detect education level
            import re
            for level, keywords in self.education_patterns.items():
                for keyword in keywords:
                    # Use word boundaries for better matching, except for abbreviations with dots
                    if '.' in keyword:
                        # For patterns like 'b.tech', 'm.tech', match as-is
                        pattern = re.escape(keyword)
                    else:
                        # For words, use word boundaries to avoid partial matches
                        pattern = r'\b' + re.escape(keyword) + r'\b'
                    
                    if re.search(pattern, text_lower):
                        self.logger.debug(f"Found keyword '{keyword}' in text for level '{level}'")
                        if level.endswith('_level'):
                            analysis['education_level'] = level.replace('_level', '')
                        elif level.endswith('_fields'):
                            analysis['field_of_study'] = level.replace('_fields', '')
                            analysis['specific_degree'] = keyword.upper()
                        break
            
            # Determine user type and progression suggestions
            if analysis['education_level'] == 'bachelor':
                if analysis['field_of_study'] == 'engineering':
                    analysis['user_type'] = 'engineering_graduate'
                    analysis['progression_suggestions'] = ['masters_in_engineering', 'mba_tech', 'professional_certifications']
                elif analysis['field_of_study'] == 'business':
                    analysis['user_type'] = 'business_graduate'
                    analysis['progression_suggestions'] = ['specialized_masters', 'professional_certifications']
                else:
                    analysis['user_type'] = 'fresh_graduate'
                    analysis['progression_suggestions'] = ['masters', 'professional_certifications']
            elif analysis['education_level'] == 'master':
                analysis['user_type'] = 'working_professional'
                analysis['progression_suggestions'] = ['executive_programs', 'doctoral_programs', 'professional_certifications']
            
            self.logger.debug(f"Educational background analysis: {analysis}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing educational background: {e}")
            return {'education_level': 'unknown', 'field_of_study': 'unknown', 'user_type': 'general'}
    
    def filter_programs_by_background(self, documents: List[Dict[str, Any]], user_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter and score programs based on user's educational background"""
        try:
            if user_analysis['education_level'] == 'unknown':
                return documents
            
            filtered_docs = []
            education_level = user_analysis['education_level']
            field_of_study = user_analysis['field_of_study']
            
            for doc in documents:
                text_lower = doc.get('text', '').lower()
                score = 0
                relevance_reasons = []
                
                # Score based on appropriate education level
                if education_level == 'bachelor':
                    # Look for postgraduate programs
                    if any(term in text_lower for term in ['master', 'mba', 'postgraduate', 'pg']):
                        score += 20
                        relevance_reasons.append('postgraduate_level_appropriate')
                    # Penalize bachelor's programs for bachelor's holders
                    if any(term in text_lower for term in ['bachelor', 'undergraduate', 'ug']) and not any(term in text_lower for term in ['master', 'mba']):
                        score -= 10
                        
                elif education_level == 'master':
                    # Look for executive or advanced programs
                    if any(term in text_lower for term in ['executive', 'advanced', 'professional', 'certificate']):
                        score += 15
                        relevance_reasons.append('advanced_level_appropriate')
                
                # Score based on field relevance
                if field_of_study == 'engineering':
                    if any(term in text_lower for term in ['technology', 'engineering', 'technical', 'digital', 'systems', 'computing']):
                        score += 15
                        relevance_reasons.append('field_relevant')
                    if any(term in text_lower for term in ['business', 'management', 'mba']):
                        score += 10  # Good for career transition
                        relevance_reasons.append('career_transition_suitable')
                        
                elif field_of_study == 'business':
                    if any(term in text_lower for term in ['business', 'management', 'finance', 'marketing', 'commerce']):
                        score += 15
                        relevance_reasons.append('field_relevant')
                
                # Add metadata
                if score > 0:
                    doc['metadata'] = doc.get('metadata', {})
                    doc['metadata']['background_relevance_score'] = score
                    doc['metadata']['relevance_reasons'] = relevance_reasons
                    filtered_docs.append((score, doc))
            
            # Sort by relevance score and return top results
            filtered_docs.sort(key=lambda x: x[0], reverse=True)
            result = [doc for score, doc in filtered_docs[:6]]
            
            self.logger.info(f"Filtered {len(documents)} to {len(result)} programs based on {education_level} in {field_of_study}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error filtering programs by background: {e}")
            return documents
    
    def format_response_by_user_type(self, response_content: str, user_analysis: Dict[str, Any], 
                                    user_name: str = "", university_name: str = "") -> str:
        """Format response based on user type and background - DISABLED for clean responses"""
        try:
            # Return original response content without additional formatting
            # This prevents template placeholders and extra formatting from appearing
            return response_content
            
            # COMMENTED OUT - User type formatting code that was causing template issues
            # user_type = user_analysis.get('user_type', 'general')
            # education_level = user_analysis.get('education_level', 'unknown')
            # 
            # # Only use specific templates if we have actual evidence of user background
            # if education_level == 'unknown' or user_type == 'general':
            #     template = self.response_templates['general']
            #     user_type = 'general'
            # else:
            #     template = self.response_templates.get(user_type, self.response_templates['general'])
            # 
            # # Create personalized intro only if we have actual user information
            # field = user_analysis.get('specific_degree', user_analysis.get('field_of_study', ''))
            # if field and field != 'unknown' and user_type != 'general':
            #     try:
            #         intro = template['intro_pattern'].format(field=field)
            #     except (KeyError, ValueError):
            #         # Fallback if template doesn't have {field} placeholder
            #         intro = template['intro_pattern']
            # else:
            #     intro = template['intro_pattern']
            # 
            # # Structure the response better
            # lines = response_content.split('\n')
            # structured_response = []
            # 
            # # Add personalized intro only if we have a name AND specific user type
            # if user_name and user_type != 'general':
            #     structured_response.append(f"Hi {user_name}! {intro}")
            #     structured_response.append("")  # Empty line after personalized intro
            # elif user_name:
            #     structured_response.append(f"Hi {user_name}! {intro}")
            #     structured_response.append("")  # Empty line after generic intro with name
            # else:
            #     # Only add intro if it's not making assumptions
            #     if user_type != 'general':
            #         structured_response.append(intro)
            #         structured_response.append("")  # Empty line only if we added intro
            #     # For general users without name, let the main content speak for itself
            # 
            # # Add context-aware content introduction only if we have evidence
            # if user_analysis.get('education_level') == 'bachelor':
            #     structured_response.append("Based on your educational background, here are the most relevant advancement options:")
            #     structured_response.append("")
            # elif user_analysis['education_level'] == 'master':
            #     structured_response.append("For someone with your qualifications, here are excellent career advancement opportunities:")
            #     structured_response.append("")
            # elif user_analysis['education_level'] != 'unknown':
            #     structured_response.append("Here are some great educational opportunities for you:")
            #     structured_response.append("")
            # # For unknown education level, don't add any assumption-based introduction
            # # and don't add extra spacing
            # 
            # # Process and improve the main content
            # current_section = []
            # for line in lines:
            #     line = line.strip()
            #     if not line:
            #         if current_section:
            #             structured_response.extend(current_section)
            #             structured_response.append("")
            #             current_section = []
            #     else:
            #         # Improve formatting of key information
            #         if any(keyword in line.lower() for keyword in ['program', 'degree', 'course']):
            #             line = f"🎓 **{line}**"
            #         elif any(keyword in line.lower() for keyword in ['duration', 'months', 'years']):
            #             line = f"⏱️ {line}"
            #         elif any(keyword in line.lower() for keyword in ['fee', 'cost', 'price']):
            #             line = f"💰 {line}"
            #         elif any(keyword in line.lower() for keyword in ['requirement', 'eligibility']):
            #             line = f"📋 {line}"
            #         
            #         current_section.append(line)
            # 
            # # Add remaining content
            # if current_section:
            #     structured_response.extend(current_section)
            # 
            # # Add call-to-action based on user type (only if we have evidence)
            # structured_response.append("")
            # if user_analysis['education_level'] == 'bachelor':
            #     structured_response.append("💡 **Next Steps:** Which of these advancement paths interests you most? I can provide detailed information about admission requirements, career prospects, and application processes!")
            # elif user_analysis['education_level'] != 'unknown':
            #     structured_response.append("💡 **Ready to Take the Next Step?** I'm here to help with detailed information about any program that catches your interest!")
            # else:
            #     # Generic call-to-action when we don't know the user's background
            #     structured_response.append("💡 **How Can I Help?** I can provide detailed information about any program that interests you - just let me know what you'd like to learn more about!")
            # 
            # return "\n".join(structured_response)
            
        except Exception as e:
            self.logger.error(f"Error formatting response by user type: {e}")
            return response_content
    
    def health_check(self) -> tuple[bool, str]:
        """Check user analyzer health"""
        try:
            # Test analyze function
            test_analysis = self.analyze_educational_background("I have a bachelor's degree in engineering")
            if test_analysis and test_analysis.get('education_level') == 'bachelor':
                return True, "User analyzer is healthy"
            else:
                return False, "User analyzer failed test analysis"
        except Exception as e:
            return False, f"User analyzer health check failed: {e}"
