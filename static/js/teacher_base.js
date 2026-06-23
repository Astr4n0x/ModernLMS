/**
 * Teacher Admin Panel Logic
 * Manages Routing, Uploads, Verification, and Live Simulation
 */

// =========================================
// 1. Mock DB Structure
// =========================================
// Instructors might only teach certain courses.
const mockAssignedCourses = [
    {
        id: 'c1',
        title: 'Physics',
        subjects: [
            { id: 's1', title: 'Dynamics' },
            { id: 's2', title: 'Thermodynamics' },
            { id: 's3', title: 'Electromagnetism' }
        ]
    },
    {
        id: 'c2',
        title: 'Mathematics',
        subjects: [
            { id: 's4', title: 'Algebra' },
            { id: 's5', title: 'Calculus' }
        ]
    }
];

// Flat structure representing the global lessons table
let lessonsDB = [
    { id: 'l1', title: 'Lesson 1: Introduction to Dynamics', courseId: 'c1', subjectId: 's1', youtubeUrl: 'https://youtube.com/watch?v=dQw4w9WgXcQ', status: 'Published' },
    { id: 'l2', title: 'Lesson 2: Newton\'s Laws', courseId: 'c1', subjectId: 's1', youtubeUrl: 'https://youtube.com/watch?v=dQw4w9WgXcQ', status: 'Published' },
    { id: 'l3', title: 'Lesson 1: Differential Equations', courseId: 'c2', subjectId: 's5', youtubeUrl: 'https://youtube.com/watch?v=dQw4w9WgXcQ', status: 'Published' }
];

// =========================================
// 2. Initialization & Module Routing
// =========================================
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initSidebarToggle();
    initLiveModule();
    initUploadForm();
    initManageTable();
});

function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item[data-target]');
    const modules = document.querySelectorAll('.module-section');
    
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Remove active class from all
            navItems.forEach(nav => nav.classList.remove('active'));
            modules.forEach(mod => {
                mod.classList.remove('active', 'animate-fade-in');
                mod.classList.add('hidden');
            });
            
            // Add active to clicked nav and target module
            item.classList.add('active');
            const targetId = item.getAttribute('data-target');
            const targetModule = document.getElementById(targetId);
            
            targetModule.classList.remove('hidden');
            // Trigger animation reflow
            void targetModule.offsetWidth; 
            targetModule.classList.add('active', 'animate-fade-in');

            // Mobile sidebar auto-close
            if (window.innerWidth <= 768) {
                document.querySelector('.sidebar').classList.remove('open');
            }
        });
    });

    // Mobile menu toggle
    document.getElementById('menu-toggle').addEventListener('click', () => {
        document.querySelector('.sidebar').classList.toggle('open');
    });
}

function initSidebarToggle() {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const toggleBtn = document.getElementById('sidebar-collapse-btn');
    
    toggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
        mainContent.classList.toggle('expanded');
    });
}

// =========================================
// 3. Live Module Logic (Selection & Viewing)
// =========================================
const activeLiveClasses = [
    { id: 'live1', title: 'Dynamics – Lesson 3: Friction forces', course: 'Physics', viewers: 142, thumb: 'ri-flask-line' },
    { id: 'live2', title: 'Algebra – Midterm Review Session', course: 'Mathematics', viewers: 89, thumb: 'ri-functions' },
    { id: 'live3', title: 'Thermodynamics – Laws and Principles', course: 'Physics', viewers: 210, thumb: 'ri-fire-line' }
];

function initLiveModule() {
    const listView = document.getElementById('live-list-view');
    const streamView = document.getElementById('live-stream-view');
    const backBtn = document.getElementById('back-to-live-list');
    const liveHeaderP = document.querySelector('#live-header p');
    const iframe = document.getElementById('live-iframe');
    const titleEl = document.getElementById('live-lesson-title');
    
    // Render list
    listView.innerHTML = '';
    activeLiveClasses.forEach(cls => {
        const card = document.createElement('div');
        card.className = 'live-card';
        card.innerHTML = `
            <div class="live-card-thumb">
                <span class="live-indicator"><span class="pulse"></span> LIVE</span>
                <i class="${cls.thumb}"></i>
            </div>
            <div class="live-card-content">
                <div class="live-card-title">${cls.title}</div>
                <div class="live-card-meta">
                    <span>${cls.course}</span>
                    <span style="color:var(--danger-color)"><i class="ri-eye-line"></i> ${cls.viewers}</span>
                </div>
            </div>
        `;
        
        // Enter Live Stream
        card.addEventListener('click', () => {
            listView.classList.add('hidden');
            streamView.classList.remove('hidden');
            backBtn.classList.remove('hidden');
            liveHeaderP.classList.add('hidden');
            
            titleEl.textContent = cls.title;
            // Note: In real app, we'd set iframe.src based on cls.id
            
            // Start fake comments
            initLiveSimulation();
        });
        
        listView.appendChild(card);
    });
    
    // Back to list
    backBtn.addEventListener('click', () => {
        streamView.classList.add('hidden');
        listView.classList.remove('hidden');
        backBtn.classList.add('hidden');
        liveHeaderP.classList.remove('hidden');
        
        // Stop fake comments
        clearInterval(liveInterval);
        document.getElementById('comments-feed').innerHTML = ''; 
    });
}

// =========================================
// 4. Upload Lesson Logic
// =========================================
function initUploadForm() {
    const courseSelect = document.getElementById('upload-course');
    const subjectSelect = document.getElementById('upload-subject');
    const form = document.getElementById('upload-form');

    // Populate Courses
    mockAssignedCourses.forEach(course => {
        const option = document.createElement('option');
        option.value = course.id;
        option.textContent = course.title;
        courseSelect.appendChild(option);
    });

    // Handle cascade update for Subjects
    courseSelect.addEventListener('change', (e) => {
        const selectedId = e.target.value;
        const course = mockAssignedCourses.find(c => c.id === selectedId);
        
        subjectSelect.innerHTML = '<option value="" disabled selected>Choose a subject</option>';
        if (course) {
            subjectSelect.disabled = false;
            course.subjects.forEach(subject => {
                const opt = document.createElement('option');
                opt.value = subject.id;
                opt.textContent = subject.title;
                subjectSelect.appendChild(opt);
            });
        }
        
        clearError(courseSelect); // Remove any existing validation errors when a user makes a choice
    });
    
    // Clear validation error on change
    subjectSelect.addEventListener('change', () => clearError(subjectSelect));
    document.getElementById('upload-title').addEventListener('input', (e) => clearError(e.target));
    document.getElementById('upload-link').addEventListener('input', (e) => clearError(e.target));
    document.getElementById('upload-desc').addEventListener('input', (e) => clearError(e.target));

    // Form Submission / Validation
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        if (validateUploadForm()) {
            publishLesson();
        }
    });
}

function processYouTubeLink(url) {
    // Basic regex to check if it matches youtube formats
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=|\?v=)([^#&?]*).*/;
    const match = url.match(regExp);
    if (match && match[2].length === 11) {
        return `https://www.youtube.com/embed/${match[2]}`;
    }
    return false;
}

function validateUploadForm() {
    let isValid = true;

    // References
    const course = document.getElementById('upload-course');
    const subject = document.getElementById('upload-subject');
    const title = document.getElementById('upload-title');
    const link = document.getElementById('upload-link');
    const desc = document.getElementById('upload-desc');

    if (!course.value) { showError(course, "Please select a course."); isValid = false; }
    if (!subject.value) { showError(subject, "Please select a subject."); isValid = false; }
    if (!title.value.trim()) { showError(title, "Lesson title is required."); isValid = false; }
    if (!desc.value.trim()) { showError(desc, "Lesson description is required."); isValid = false; }
    
    // Custom Link validation
    if (!link.value.trim() || !processYouTubeLink(link.value)) {
        showError(link, "Invalid YouTube link format. Please provide a valid URL.");
        isValid = false;
    }

    return isValid;
}

function showError(element, message) {
    const formGroup = element.closest('.form-group');
    formGroup.classList.add('has-error');
    formGroup.querySelector('.error-msg').textContent = message;
}

function clearError(element) {
    const formGroup = element.closest('.form-group');
    formGroup.classList.remove('has-error');
}

function publishLesson() {
    const title = document.getElementById('upload-title').value;
    const courseId = document.getElementById('upload-course').value;
    const subjectId = document.getElementById('upload-subject').value;
    const link = document.getElementById('upload-link').value;
    
    // Add to mock DB
    const newLesson = {
        id: `l${Date.now()}`,
        title: title,
        courseId: courseId,
        subjectId: subjectId,
        youtubeUrl: link,
        status: 'Published'
    };
    
    lessonsDB.push(newLesson);
    
    // Reset Form
    document.getElementById('upload-form').reset();
    document.getElementById('upload-subject').disabled = true;
    
    // Update manage table
    renderManageTable();
    
    // Show Toast Notification
    showToast("Lesson published successfully!");
}

// =========================================
// 5. Manage Table Logic
// =========================================
function initManageTable() {
    renderManageTable();
}

function renderManageTable() {
    const tbody = document.getElementById('manage-table-body');
    tbody.innerHTML = '';
    
    // Sort array so newest is at the top
    const displayList = [...lessonsDB].reverse();

    displayList.forEach(lesson => {
        // Resolve names
        const c = mockAssignedCourses.find(c => c.id === lesson.courseId);
        const s = c ? c.subjects.find(s => s.id === lesson.subjectId) : null;
        
        const courseName = c ? c.title : 'Unknown';
        const subjectName = s ? s.title : 'Unknown';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${lesson.title}</strong></td>
            <td><span style="color:var(--text-secondary);font-size:0.875rem">${courseName} / ${subjectName}</span></td>
            <td><span class="status-badge status-published">${lesson.status}</span></td>
            <td>
                <div class="action-buttons">
                    <button class="btn-action" title="Edit" onclick="showToast('Edit modal opened')"><i class="ri-edit-line"></i></button>
                    <button class="btn-action" title="Schedule Live Class" onclick="showToast('Schedule modal opened')"><i class="ri-calendar-event-line"></i></button>
                    <button class="btn-action delete" title="Delete" onclick="deleteLesson('${lesson.id}')"><i class="ri-delete-bin-line"></i></button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function deleteLesson(id) {
    if(confirm("Are you sure you want to delete this lesson?")) {
        lessonsDB = lessonsDB.filter(l => l.id !== id);
        renderManageTable();
        showToast("Lesson deleted successfully.");
    }
}

// =========================================
// 6. Live Simulation Logic (Chat)
// =========================================
const mockComments = [
    { author: "Rahim", text: "Good morning sir! Ready for class." },
    { author: "Sara", text: "Can you explain the last formula again?" },
    { author: "John Doe", text: "This part is confusing, what does the coefficient represent?" },
    { author: "Emily C.", text: "Ah, that makes sense now. Thank you!" },
    { author: "Kevin M.", text: "Will this be on the final exam?" }
];

let liveInterval;
function initLiveSimulation() {
    const feed = document.getElementById('comments-feed');
    let index = 0;

    // Generate fake comments every 5 seconds for realism
    liveInterval = setInterval(() => {
        // Stop generating if we run out, though we could loop
        if (index >= mockComments.length) {
            index = 0; // loop forever
        }

        const commentData = mockComments[index];
        const commentEl = document.createElement('div');
        commentEl.className = 'comment';
        
        const now = new Date();
        const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

        commentEl.innerHTML = `
            <div class="comment-meta">
                <span class="comment-author">${commentData.author}</span>
                <span class="comment-time">${timeStr}</span>
            </div>
            <div class="comment-text">${commentData.text}</div>
        `;
        
        feed.appendChild(commentEl);
        
        // Auto scroll
        feed.scrollTop = feed.scrollHeight;

        index++;
    }, 4500);
}

// =========================================
// 7. Global Utilities
// =========================================
function showToast(message) {
    const toast = document.getElementById('toast');
    document.getElementById('toast-msg').textContent = message;
    
    toast.classList.remove('hidden');
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}
