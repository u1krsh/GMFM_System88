"""
Generate Detailed Architecture Diagram for MotorMeasure Pro
With proper 16:9 aspect ratio and clear, legible text
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle
import numpy as np
import os

# Get the script directory for saving files
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Modern color palette
COLORS = {
    'primary': '#0D9488',      # Teal
    'secondary': '#10B981',    # Emerald
    'accent': '#8B5CF6',       # Violet
    'warning': '#F59E0B',      # Amber
    'dark': '#0F172A',         # Slate 900
    'medium': '#1E293B',       # Slate 800
    'light': '#334155',        # Slate 700
    'text': '#F8FAFC',         # Almost white
    'muted': '#94A3B8',        # Slate 400
    'rose': '#F43F5E',         # Rose
    'sky': '#0EA5E9',          # Sky
    'cyan': '#06B6D4',         # Cyan
}


def create_system_architecture():
    """Create architecture diagram with 16:9 aspect ratio, no overlaps, legible text"""
    fig, ax = plt.subplots(1, 1, figsize=(16, 9))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['dark'])
    ax.set_facecolor(COLORS['dark'])
    
    # Title
    ax.text(8, 8.6, 'MotorMeasure Pro - System Architecture', 
            fontsize=22, fontweight='bold', color=COLORS['text'],
            ha='center', va='center')
    
    # ========== USER LAYER (Row 1) ==========
    user_box = FancyBboxPatch((6, 7.7), 4, 0.7, boxstyle="round,pad=0.03,rounding_size=0.1",
                               facecolor=COLORS['accent'], edgecolor=COLORS['text'], linewidth=2)
    ax.add_patch(user_box)
    ax.text(8, 8.05, 'Clinician / Therapist', fontsize=12, fontweight='bold', 
            color=COLORS['text'], ha='center', va='center')
    
    # ========== PRESENTATION LAYER (Row 2) ==========
    views_box = FancyBboxPatch((0.3, 5.6), 15.4, 1.8, boxstyle="round,pad=0.03,rounding_size=0.12",
                                facecolor=COLORS['primary'], edgecolor=COLORS['text'], linewidth=2)
    ax.add_patch(views_box)
    ax.text(8, 7.15, 'PRESENTATION LAYER (Flet UI)', fontsize=13, fontweight='bold', 
            color=COLORS['text'], ha='center', va='center')
    
    views = ['Dashboard', 'Scoring', 'Session', 'Student', 'Settings']
    for i, name in enumerate(views):
        x = 0.6 + i * 3.05
        view_box = FancyBboxPatch((x, 5.75), 2.8, 1.1, boxstyle="round,pad=0.02,rounding_size=0.08",
                                   facecolor=COLORS['medium'], edgecolor=COLORS['light'], linewidth=1.5)
        ax.add_patch(view_box)
        ax.text(x + 1.4, 6.3, f'{name} View', fontsize=11, color=COLORS['text'], 
                ha='center', va='center', fontweight='bold')
    
    # ========== SERVICES LAYER (Row 3) ==========
    services_box = FancyBboxPatch((0.3, 3.2), 15.4, 2.1, boxstyle="round,pad=0.03,rounding_size=0.12",
                                   facecolor=COLORS['secondary'], edgecolor=COLORS['text'], linewidth=2)
    ax.add_patch(services_box)
    ax.text(8, 5.05, 'SERVICES LAYER', fontsize=13, fontweight='bold', 
            color=COLORS['text'], ha='center', va='center')
    
    services = [
        ('Chart', COLORS['sky']),
        ('Report', COLORS['accent']),
        ('DOCX Import', COLORS['warning']),
        ('Instructions', COLORS['cyan']),
        ('Security', COLORS['rose']),
        ('Haptics', COLORS['primary']),
    ]
    for i, (name, color) in enumerate(services):
        x = 0.5 + i * 2.55
        svc_box = FancyBboxPatch((x, 3.4), 2.35, 1.35, boxstyle="round,pad=0.02,rounding_size=0.1",
                                  facecolor=color, edgecolor=COLORS['text'], linewidth=1.5)
        ax.add_patch(svc_box)
        ax.text(x + 1.175, 4.08, name, fontsize=11, color=COLORS['text'], 
                ha='center', va='center', fontweight='bold')
    
    # ========== BOTTOM ROW: Scoring + Data (Row 4) ==========
    # Scoring Engine - LEFT
    scoring_box = FancyBboxPatch((0.3, 0.5), 7.3, 2.4, boxstyle="round,pad=0.03,rounding_size=0.12",
                                  facecolor=COLORS['warning'], edgecolor=COLORS['text'], linewidth=2)
    ax.add_patch(scoring_box)
    ax.text(3.95, 2.65, 'SCORING ENGINE', fontsize=12, fontweight='bold', 
            color=COLORS['dark'], ha='center', va='center')
    
    scoring_comps = ['Engine', 'Catalog', 'Items JSON']
    for i, name in enumerate(scoring_comps):
        x = 0.6 + i * 2.35
        comp_box = FancyBboxPatch((x, 0.7), 2.1, 1.5, boxstyle="round,pad=0.02,rounding_size=0.08",
                                   facecolor=COLORS['medium'], edgecolor=COLORS['light'], linewidth=1.5)
        ax.add_patch(comp_box)
        ax.text(x + 1.05, 1.45, name, fontsize=11, color=COLORS['text'], 
                ha='center', va='center', fontweight='bold')
    
    # Data Layer - RIGHT
    data_box = FancyBboxPatch((7.9, 0.5), 7.8, 2.4, boxstyle="round,pad=0.03,rounding_size=0.12",
                               facecolor=COLORS['sky'], edgecolor=COLORS['text'], linewidth=2)
    ax.add_patch(data_box)
    ax.text(11.8, 2.65, 'DATA LAYER', fontsize=12, fontweight='bold', 
            color=COLORS['text'], ha='center', va='center')
    
    data_comps = [('Database', 'SQLite'), ('Models', 'Pydantic'), ('Repository', 'CRUD'), ('Export', 'PDF')]
    for i, (name, tech) in enumerate(data_comps):
        x = 8.15 + i * 1.9
        comp_box = FancyBboxPatch((x, 0.7), 1.7, 1.5, boxstyle="round,pad=0.02,rounding_size=0.08",
                                   facecolor=COLORS['medium'], edgecolor=COLORS['light'], linewidth=1.5)
        ax.add_patch(comp_box)
        ax.text(x + 0.85, 1.65, name, fontsize=10, color=COLORS['text'], 
                ha='center', va='center', fontweight='bold')
        ax.text(x + 0.85, 1.15, tech, fontsize=9, color=COLORS['muted'], 
                ha='center', va='center')
    
    # ========== ARROWS ==========
    # User to Presentation
    ax.annotate('', xy=(8, 7.4), xytext=(8, 7.7),
                arrowprops=dict(arrowstyle='<->', color=COLORS['text'], lw=2.5))
    # Presentation to Services  
    ax.annotate('', xy=(8, 5.3), xytext=(8, 5.6),
                arrowprops=dict(arrowstyle='<->', color=COLORS['text'], lw=2.5))
    # Services to Scoring
    ax.annotate('', xy=(3.95, 2.9), xytext=(3.95, 3.2),
                arrowprops=dict(arrowstyle='<->', color=COLORS['text'], lw=2.5))
    # Services to Data
    ax.annotate('', xy=(11.8, 2.9), xytext=(11.8, 3.2),
                arrowprops=dict(arrowstyle='<->', color=COLORS['text'], lw=2.5))
    
    plt.tight_layout()
    output_path = os.path.join(SCRIPT_DIR, 'architecture_diagram.png')
    plt.savefig(output_path, dpi=200, facecolor=COLORS['dark'], 
                edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"Architecture diagram saved: {output_path}")
    return output_path


def create_workflow_diagram():
    """Create workflow diagram with 16:9 aspect ratio"""
    fig, ax = plt.subplots(1, 1, figsize=(16, 9))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['dark'])
    ax.set_facecolor(COLORS['dark'])
    
    # Title
    ax.text(8, 8.5, 'MotorMeasure Pro - Clinical Workflow', 
            fontsize=22, fontweight='bold', color=COLORS['text'],
            ha='center', va='center')
    
    # Main workflow row
    steps = [
        ('1', 'Add Patient', COLORS['primary']),
        ('2', 'Start Session', COLORS['secondary']),
        ('3', 'Score Items', COLORS['sky']),
        ('4', 'Review Results', COLORS['accent']),
        ('5', 'Export Report', COLORS['warning']),
    ]
    
    for i, (num, title, color) in enumerate(steps):
        x = 1.5 + i * 2.8
        
        circle = plt.Circle((x, 6.5), 0.55, facecolor=color, edgecolor=COLORS['text'], linewidth=2)
        ax.add_patch(circle)
        ax.text(x, 6.5, num, fontsize=20, fontweight='bold', 
                color=COLORS['text'], ha='center', va='center')
        ax.text(x, 5.6, title, fontsize=11, fontweight='bold', 
                color=color, ha='center', va='center')
        
        if i < len(steps) - 1:
            ax.annotate('', xy=(x + 2, 6.5), xytext=(x + 0.75, 6.5),
                        arrowprops=dict(arrowstyle='->', color=COLORS['text'], lw=2.5))
    
    # Supporting services
    ax.text(8, 4.3, 'Supporting Services', fontsize=14, fontweight='bold', 
            color=COLORS['text'], ha='center', va='center')
    
    services = [
        ('Scoring Engine', COLORS['warning']),
        ('Chart Service', COLORS['sky']),
        ('Security', COLORS['rose']),
        ('Instructions', COLORS['cyan']),
    ]
    for i, (name, color) in enumerate(services):
        x = 1.2 + i * 3.6
        svc_box = FancyBboxPatch((x, 2.8), 3.2, 1.1, boxstyle="round,pad=0.02,rounding_size=0.1",
                                  facecolor=color, edgecolor=COLORS['text'], linewidth=1.5)
        ax.add_patch(svc_box)
        ax.text(x + 1.6, 3.35, name, fontsize=12, color=COLORS['text'], 
                ha='center', va='center', fontweight='bold')
    
    # Outputs
    ax.text(8, 1.7, 'Outputs', fontsize=13, fontweight='bold', color=COLORS['text'], ha='center')
    outputs = ['PDF Scoresheets', 'Trend Charts', 'Session History', 'Encrypted DB']
    for i, out in enumerate(outputs):
        x = 1.2 + i * 3.6
        out_box = FancyBboxPatch((x, 0.4), 3.2, 0.9, boxstyle="round,pad=0.02,rounding_size=0.08",
                                  facecolor=COLORS['medium'], edgecolor=COLORS['light'], linewidth=1.5)
        ax.add_patch(out_box)
        ax.text(x + 1.6, 0.85, out, fontsize=11, color=COLORS['text'], 
                ha='center', va='center', fontweight='bold')
    
    plt.tight_layout()
    output_path = os.path.join(SCRIPT_DIR, 'workflow_diagram.png')
    plt.savefig(output_path, dpi=200, facecolor=COLORS['dark'], 
                edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"Workflow diagram saved: {output_path}")
    return output_path


def create_problem_diagram():
    """Create problem space diagram with 16:9 aspect ratio"""
    fig, ax = plt.subplots(1, 1, figsize=(16, 9))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.set_aspect('equal')
    ax.axis('off')
    fig.patch.set_facecolor(COLORS['dark'])
    ax.set_facecolor(COLORS['dark'])
    
    # Title
    ax.text(8, 8.5, 'The Problem Space', fontsize=22, fontweight='bold', 
            color=COLORS['text'], ha='center', va='center')
    
    # Three columns - TOP ROW
    # Who needs this
    who_box = FancyBboxPatch((0.4, 4.3), 4.8, 3.8, boxstyle="round,pad=0.04,rounding_size=0.15",
                              facecolor=COLORS['primary'], edgecolor=COLORS['text'], linewidth=2)
    ax.add_patch(who_box)
    ax.text(2.8, 7.7, 'Target Users', fontsize=14, fontweight='bold', 
            color=COLORS['text'], ha='center', va='center')
    who_items = ['Physiotherapists', 'Pediatric Neurologists', 'Rehab Centers', 'Special Ed Schools']
    for i, item in enumerate(who_items):
        ax.text(2.8, 6.9 - i * 0.6, '> ' + item, fontsize=12, 
                color=COLORS['text'], ha='center', va='center')
    
    # Current problems
    problem_box = FancyBboxPatch((5.6, 4.3), 4.8, 3.8, boxstyle="round,pad=0.04,rounding_size=0.15",
                                  facecolor=COLORS['rose'], edgecolor=COLORS['text'], linewidth=2)
    ax.add_patch(problem_box)
    ax.text(8, 7.7, 'Current Problems', fontsize=14, fontweight='bold', 
            color=COLORS['text'], ha='center', va='center')
    problems = ['Paper-based scoring', 'Manual calculations', 'No progress tracking', 'Data insecurity']
    for i, item in enumerate(problems):
        ax.text(8, 6.9 - i * 0.6, '> ' + item, fontsize=12, 
                color=COLORS['text'], ha='center', va='center')
    
    # Market size
    market_box = FancyBboxPatch((10.8, 4.3), 4.8, 3.8, boxstyle="round,pad=0.04,rounding_size=0.15",
                                 facecolor=COLORS['secondary'], edgecolor=COLORS['text'], linewidth=2)
    ax.add_patch(market_box)
    ax.text(13.2, 7.7, 'Market Size', fontsize=14, fontweight='bold', 
            color=COLORS['text'], ha='center', va='center')
    ax.text(13.2, 6.6, '17M+', fontsize=30, fontweight='bold', color=COLORS['text'], ha='center')
    ax.text(13.2, 5.9, 'CP patients globally', fontsize=11, color=COLORS['text'], ha='center')
    ax.text(13.2, 5.1, '2-3 per 1000', fontsize=16, fontweight='bold', color=COLORS['text'], ha='center')
    ax.text(13.2, 4.6, 'live births', fontsize=11, color=COLORS['text'], ha='center')
    
    # BOTTOM ROW - Why existing solutions fail
    fail_box = FancyBboxPatch((0.4, 0.4), 15.2, 3.5, boxstyle="round,pad=0.04,rounding_size=0.15",
                               facecolor=COLORS['warning'], edgecolor=COLORS['text'], linewidth=2)
    ax.add_patch(fail_box)
    ax.text(8, 3.55, 'Why Existing Solutions Fail', fontsize=16, fontweight='bold', 
            color=COLORS['dark'], ha='center', va='center')
    
    failures = [('Expensive', 'Costly licenses'), ('Cloud-Only', 'No offline support'), 
                ('No Local Apps', 'No Indian market'), ('Poor Security', 'Basic protection')]
    for i, (title, desc) in enumerate(failures):
        x = 2.3 + i * 3.5
        ax.text(x, 2.6, title, fontsize=13, fontweight='bold', color=COLORS['dark'], ha='center')
        ax.text(x, 1.9, desc, fontsize=11, color=COLORS['dark'], ha='center')
    
    plt.tight_layout()
    output_path = os.path.join(SCRIPT_DIR, 'problem_diagram.png')
    plt.savefig(output_path, dpi=200, facecolor=COLORS['dark'], 
                edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"Problem diagram saved: {output_path}")
    return output_path


if __name__ == "__main__":
    print("Generating architecture diagrams...")
    arch_path = create_system_architecture()
    workflow_path = create_workflow_diagram()
    problem_path = create_problem_diagram()
    print("\nAll diagrams generated successfully!")
    print(f"  1. {arch_path}")
    print(f"  2. {workflow_path}")
    print(f"  3. {problem_path}")
