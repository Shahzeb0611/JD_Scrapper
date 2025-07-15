import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class JobListing:
    """Data class to structure job information"""
    title: str
    category: str
    company: str
    location: str
    description: str
    requirements: str
    salary: Optional[str]
    technology_stack: List[str]  # New field for tech stack
    url: str
    posted_date: Optional[str]
    scraped_date: str
    source_website: str
    
    def to_dict(self) -> Dict:
        return asdict(self)

class JobScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        

        # Define job categories and their keywords (specific, no broad "Backend" or "Frontend")

        self.categories = {
            'Python': ['python', 'django', 'flask', 'fastapi', 'python developer'],
            'NodeJS': ['nodejs', 'node.js', 'express', 'express.js', 'server-side javascript'],
            'DotNET': ['.net', 'dotnet', 'asp.net', 'c#', 'csharp', 'vb.net', 'wpf', 'mvc', 'blazor'],
            'React': ['react', 'reactjs', 'react.js', 'react developer'],
            'Angular': ['angular', 'angularjs', 'angular developer'],
            'Vue': ['vue', 'vue.js', 'vuejs', 'vue developer'],
            'AI': ['artificial intelligence', 'ai engineer', 'machine learning', 'deep learning', 'neural networks', 'computer vision', 'nlp', 'reinforcement learning', 'ai specialist', 'deep learning specialist'],
            'Data Science': ['data scientist', 'data science', 'predictive modeling', 'data analysis', 'statistical modeling', 'data mining', 'data visualization', 'analytics', 'pandas', 'numpy', 'quantitative analyst', 'analytics consultant'],
            'Database': ['database', 'sql', 'mysql', 'postgresql', 'mongodb', 'oracle', 'sql server', 'nosql', 'dba', 'data engineer', 'data architect', 'database administrator', 'data warehouse architect', 'bi developer'],
            'Android': ['android developer', 'android studio', 'kotlin', 'java android', 'android sdk', 'android mobile apps'],
            'iOS': ['ios developer', 'swift', 'xcode', 'objective-c', 'cocoa touch', 'ios sdk', 'apple developer'],
            'Mobile Cross-Platform': ['mobile developer', 'react native', 'flutter', 'cross-platform mobile', 'hybrid mobile apps', 'xamarin'],
            'Product Management': ['product manager', 'associate product manager', 'technical product manager', 'growth product manager', 'digital product manager', 'product marketing manager', 'product design manager', 'ux product design manager', 'product analyst'],
            'Business Analysis': ['business analyst', 'junior business analyst', 'senior business analyst', 'lead business analyst', 'it business analyst', 'business systems analyst', 'business process analyst'],
            'Data Analytics': ['data analyst', 'analytics consultant', 'marketing analyst', 'financial analyst', 'operations research analyst', 'bi analyst', 'commercial analyst'],
            'BI': ['bi developer', 'bi engineer', 'bi analyst', 'bi solutions architect', 'data visualization specialist'],
            'Data Infrastructure': ['data engineer', 'data architect', 'database administrator', 'data warehouse architect'],
            'ML Engineering': ['machine learning engineer', 'machine learning scientist'],
            'Leadership': ['chief data officer', 'chief analytics officer', 'director of data strategy', 'project manager', 'business development manager', 'marketing manager', 'operations manager', 'management consultant', 'strategy manager', 'associate consultant', 'senior consultant', 'engagement manager', 'principal consultant', 'partner', 'director', 'managing director']
        }


        # Define technology stack keywords to extract
        self.tech_stack_keywords = {
            # Programming Languages
            'python', 'java', 'javascript', 'typescript', 'c#', 'c++', 'c', 'php', 'ruby', 'go', 'rust', 'swift', 'kotlin', 'scala', 'r',
            
            # Web Frameworks
            'django', 'flask', 'fastapi', 'react', 'angular', 'vue', 'node.js', 'express', 'laravel', 'spring', 'ruby on rails',
            
            # Databases
            'mysql', 'postgresql', 'mongodb', 'sqlite', 'oracle', 'sql server', 'redis', 'cassandra', 'dynamodb', 'elasticsearch',
            
            # Cloud & DevOps
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'terraform', 'ansible', 'github actions', 'gitlab ci',
            
            # Tools & Technologies
            'git', 'linux', 'unix', 'nginx', 'apache', 'rabbitmq', 'kafka', 'spark', 'hadoop', 'airflow',
            
            # Testing & Quality
            'pytest', 'junit', 'selenium', 'cypress', 'jest', 'mocha', 'postman',
            
            # Data Science & ML
            'pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch', 'keras', 'jupyter', 'tableau', 'power bi',
            
            # Mobile
            'android', 'ios', 'react native', 'flutter', 'xamarin',
            
            # Other
            'microservices', 'rest api', 'graphql', 'websockets', 'oauth', 'jwt', 'ci/cd', 'agile', 'scrum'
        }
        
        # Website configurations
        self.website_configs = {
            'linkedin': {
                'base_url': 'https://www.linkedin.com',
                'job_search_path': '/jobs/search/?keywords={}&location={}',
                'selectors': {
                    'job_cards': '.job-search-card',
                    'title': '.base-search-card__title',
                    'company': '.base-search-card__subtitle',
                    'location': '.job-search-card__location',
                    'link': '.base-card__full-link'
                }
            },
            'indeed': {
                'base_url': 'https://indeed.com',
                'job_search_path': '/jobs?q={}&l={}',
                'selectors': {
                    'job_cards': '[data-jk]',
                    'title': '[data-testid="job-title"]',
                    'company': '[data-testid="company-name"]',
                    'location': '[data-testid="job-location"]',
                    'link': 'a[data-jk]'
                }
            },'remoteok': {
                'base_url': 'https://remoteok.com',
                'job_search_path': '/remote-{}-jobs',
                'selectors': {
                    'job_cards': 'tr.job',
                    'title': 'td.position h2',
                    'company': 'td.company h3',
                    'location': 'div.location',
                    'link': 'a.preventLink'
                }
            }

        }
    
    def clean_text(self, text: str) -> str:
        """Clean text by removing asterisks and extra whitespace"""
        if not text:
            return ""
        
        # Remove asterisks and other unwanted characters
        cleaned = re.sub(r'\*+', '', text)
        
        # Remove extra whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Remove common job board artifacts
        cleaned = re.sub(r'new\s*!?$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'hiring\s*!?$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'urgent\s*!?$', '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def extract_technology_stack(self, title: str, description: str, requirements: str) -> List[str]:
        """Extract technology stack from job title, description, and requirements"""
        # Combine all text for analysis
        full_text = f"{title} {description} {requirements}".lower()
        
        # Find matching technologies
        found_technologies = set()
        
        for tech in self.tech_stack_keywords:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(tech.lower()) + r'\b'
            if re.search(pattern, full_text):
                found_technologies.add(tech.title())
        
        # Special handling for common variations
        tech_variations = {
            'nodejs': 'Node.js',
            'node js': 'Node.js',
            'reactjs': 'React',
            'react.js': 'React',
            'vuejs': 'Vue',
            'vue.js': 'Vue',
            'angularjs': 'Angular',
            'c sharp': 'C#',
            'dot net': '.NET',
            'dotnet': '.NET',
            'postgresql': 'PostgreSQL',
            'mongo db': 'MongoDB',
            'sql server': 'SQL Server',
            'amazon web services': 'AWS',
            'google cloud': 'GCP',
            'machine learning': 'Machine Learning',
            'artificial intelligence': 'AI',
            'deep learning': 'Deep Learning'
        }
        
        for variation, standard in tech_variations.items():
            if re.search(r'\b' + re.escape(variation) + r'\b', full_text):
                found_technologies.add(standard)
        
        return sorted(list(found_technologies))
    
    def categorize_job(self, title: str, description: str) -> str:
        """Categorize job based on title and description"""
        title_lower = title.lower()
        description_lower = description.lower()
        
        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword in title_lower or keyword in description_lower:
                    return category
        
        return 'Other'
    
    def extract_salary(self, text: str) -> Optional[str]:
        """Extract salary information from text"""
        salary_patterns = [
            r'\$[\d,]+\s*-\s*\$[\d,]+',
            r'\$[\d,]+k?\s*-\s*\$[\d,]+k?',
            r'\$[\d,]+(?:\.\d+)?k?',
            r'[\d,]+\s*-\s*[\d,]+\s*(?:per year|annually|yearly)',
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def scrape_job_details(self, job_url: str, source_website: str) -> Dict:
        """Scrape detailed job information from job URL"""
        try:
            response = self.session.get(job_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract job details based on website
            if source_website == 'linkedin':
                return self._scrape_linkedin_details(soup)
            elif source_website == 'indeed':
                return self._scrape_indeed_details(soup)
            elif source_website == 'remoteok':
                return self._scrape_remoteok_details(soup)

            
        except Exception as e:
            logger.error(f"Error scraping job details from {job_url}: {str(e)}")
            return {}
    
    def _scrape_linkedin_details(self, soup: BeautifulSoup) -> Dict:
        """Extract LinkedIn job details"""
        description = ""
        requirements = ""
        
        # LinkedIn job description selectors
        desc_selectors = [
            '.show-more-less-html__markup',
            '.jobs-description-content__text',
            '.jobs-box__html-content'
        ]
        
        for selector in desc_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                description = self.clean_text(desc_elem.get_text(strip=True))
                break
        
        # Extract requirements (usually in bullet points or specific sections)
        req_keywords = ['requirements', 'qualifications', 'skills', 'experience']
        for keyword in req_keywords:
            req_section = soup.find(text=re.compile(keyword, re.IGNORECASE))
            if req_section:
                parent = req_section.parent
                if parent:
                    requirements = self.clean_text(parent.get_text(strip=True))
                    break
        
        return {
            'description': description,
            'requirements': requirements,
            'salary': self.extract_salary(description)
        }
    
    def _scrape_indeed_details(self, soup: BeautifulSoup) -> Dict:
        """Extract Indeed job details"""
        description = ""
        requirements = ""
        
        # Indeed job description selectors
        desc_selectors = [
            '.jobsearch-jobDescriptionText',
            '.jobsearch-JobComponent-description',
            '#jobDescriptionText'
        ]
        
        for selector in desc_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                description = self.clean_text(desc_elem.get_text(strip=True))
                break
        
        # Extract salary from Indeed's salary section
        salary_elem = soup.select_one('.icl-u-xs-mr--xs .attribute_snippet')
        salary = salary_elem.get_text(strip=True) if salary_elem else self.extract_salary(description)
        
        return {
            'description': description,
            'requirements': requirements,
            'salary': salary
        }
    
    def _scrape_remoteok_details(self, soup: BeautifulSoup) -> Dict:
        """Extract RemoteOK job details"""
        description = ""
        requirements = ""
        salary = None

        # RemoteOK job descriptions are in a <div class="description">
        desc_elem = soup.select_one('div.description')
        if desc_elem:
            description = self.clean_text(desc_elem.get_text(strip=True))

        # Salary sometimes exists in a <div class="salary"> or can be extracted from description
        salary_elem = soup.select_one('div.salary')
        if salary_elem:
            salary = self.extract_salary(salary_elem.get_text(strip=True))
        else:
            salary = self.extract_salary(description)

        return {
            'description': description,
            'requirements': requirements,
            'salary': salary
        }

    
    def scrape_website(self, website: str, categories: List[str], location: str = "", max_jobs: int = 50) -> List[JobListing]:
        """Scrape jobs from a specific website"""
        if website not in self.website_configs:
            logger.error(f"Website {website} not supported")
            return []
        
        config = self.website_configs[website]
        jobs = []
        
        for category in categories:
            logger.info(f"Scraping {category} jobs from {website}")
            
            # Build search URL
            search_url = config['base_url'] + config['job_search_path'].format(category, location)
            
            try:
                response = self.session.get(search_url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find job cards
                job_cards = soup.select(config['selectors']['job_cards'])
                
                for i, card in enumerate(job_cards[:max_jobs]):
                    if i >= max_jobs:
                        break
                    
                    try:
                        # Extract basic job info
                        title_elem = card.select_one(config['selectors']['title'])
                        company_elem = card.select_one(config['selectors']['company'])
                        location_elem = card.select_one(config['selectors']['location'])
                        link_elem = card.select_one(config['selectors']['link'])
                        
                        if not all([title_elem, company_elem, link_elem]):
                            continue
                        
                        # Clean the extracted text
                        title = self.clean_text(title_elem.get_text(strip=True))
                        company = self.clean_text(company_elem.get_text(strip=True))
                        job_location = self.clean_text(location_elem.get_text(strip=True)) if location_elem else "Not specified"
                        
                        # Skip if essential information is missing after cleaning
                        if not title or not company:
                            continue
                        
                        # Get job URL
                        job_url = link_elem.get('href')
                        if job_url and not job_url.startswith('http'):
                            job_url = urljoin(config['base_url'], job_url)
                        
                        # Scrape detailed job information
                        job_details = self.scrape_job_details(job_url, website)
                        
                        # Extract technology stack
                        tech_stack = self.extract_technology_stack(
                            title, 
                            job_details.get('description', ''), 
                            job_details.get('requirements', '')
                        )
                        
                        # Determine job category
                        job_category = self.categorize_job(title, job_details.get('description', ''))
                        
                        # Only include jobs that match our target categories
                        if job_category in self.categories:
                            job = JobListing(
                                category=job_category,
                                title=title,
                                company=company,
                                location=job_location,
                                description=job_details.get('description', ''),
                                requirements=job_details.get('requirements', ''),
                                salary=job_details.get('salary'),
                                technology_stack=tech_stack,  # Include tech stack
                                url=job_url,
                                posted_date=None,  # Could be extracted if available
                                scraped_date=datetime.now().isoformat(),
                                source_website=website
                            )
                            jobs.append(job)
                            
                        # Add delay to avoid being blocked
                        time.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error processing job card: {str(e)}")
                        continue
                
            except Exception as e:
                logger.error(f"Error scraping {website} for {category}: {str(e)}")
                continue
        
        return jobs
    
    def scrape_all_websites(self, websites: List[str], categories: List[str], location: str = "", max_jobs_per_site: int = 50) -> List[Dict]:
        """Scrape jobs from multiple websites"""
        all_jobs = []
        
        for website in websites:
            logger.info(f"Starting to scrape {website}")
            jobs = self.scrape_website(website, categories, location, max_jobs_per_site)
            all_jobs.extend([job.to_dict() for job in jobs])
            
            # Add delay between websites
            time.sleep(2)
        
        return all_jobs
    
#    def save_to_json(self, jobs: List[Dict], filename: str):
#        """Save jobs to JSON file"""
#        with open(filename, 'w', encoding='utf-8') as f:
#            json.dump(jobs, f, indent=2, ensure_ascii=False)
#        
#        logger.info(f"Saved {len(jobs)} jobs to {filename}")
        
    def save_to_json(self, jobs: List[Dict], filename: str):
        """Save jobs to JSON file with numbered keys like JD001, JD002"""
        
        # Convert list to dict with keys JD001, JD002, etc.
        jobs_dict = {
            f"JD{str(index + 1).zfill(3)}": job
            for index, job in enumerate(jobs)
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(jobs_dict, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(jobs)} jobs to {filename}")

# Example usage
if __name__ == "__main__":
    scraper = JobScraper()

    # Configuration
    websites = ['linkedin','remoteok']
    categories = [
        'Python',
        # 'NodeJS',
        # 'DotNET',
        # 'React',
        # 'Angular',
        # 'Vue',
        'AI',
        'Data Science',
        'Database',
        # 'Android',
        # 'iOS',
        # 'Mobile Cross-Platform',
        # 'Product Management',
        'Business Analysis',
        'Data Analytics',
        'BI',
        # 'Data Infrastructure',
        'ML Engineering',
        # 'Leadership'
    ]

    locations = [                      
        "Australia",                                
        # "United Kingdom",              
        # "Pakistan",         
    ]

    max_jobs_per_site = 20

    all_jobs = []

    # Iterating for multiple locations
    for location in locations:
        print(f"\n📍 Scraping jobs for location: {location}")
        jobs = scraper.scrape_all_websites(
            websites=websites,
            categories=categories,
            location=location,  # correct: single string
            max_jobs_per_site=max_jobs_per_site
        )
        all_jobs.extend(jobs)

    # Save to JSON
    scraper.save_to_json(all_jobs, 'scraped_jobs_new_ids.json')

    # Summary Output
    print(f"\nTotal jobs scraped: {len(all_jobs)}\n")

    category_counts = {}
    tech_stack_counts = {}

    for job in all_jobs:
        category = job['category']
        category_counts[category] = category_counts.get(category, 0) + 1

        for tech in job['technology_stack']:
            tech_stack_counts[tech] = tech_stack_counts.get(tech, 0) + 1

    print("Jobs by category:")
    for category, count in category_counts.items():
        print(f"  {category}: {count}")

    print("\nTop 10 technologies mentioned:")
    sorted_tech = sorted(tech_stack_counts.items(), key=lambda x: x[1], reverse=True)
    for tech, count in sorted_tech[:10]:
        print(f"  {tech}: {count}")
