/**
 * GitPulse Frontend Application
 */

const API_BASE = '/api';

// State
let repositories = [];
let leaderboard = [];
let globalScores = null;
let repoScores = [];
let contributionChart = null;
let repoScoresChart = null;

// DOM Elements
const elements = {
    ollamaStatus: document.getElementById('ollama-status'),
    analyzeAllBtn: document.getElementById('analyze-all-btn'),
    discoverBtn: document.getElementById('discover-btn'),
    reposList: document.getElementById('repositories-list'),
    repoScoresGrid: document.getElementById('repo-scores-grid'),
    leaderboardBody: document.getElementById('leaderboard-body'),
    leaderboardRepoSelect: document.getElementById('leaderboard-repo-select'),
    analysisStatus: document.getElementById('analysis-status'),
    totalRepos: document.getElementById('total-repos'),
    totalContributors: document.getElementById('total-contributors'),
    totalCommits: document.getElementById('total-commits'),
    avgQuality: document.getElementById('avg-quality'),
    toast: document.getElementById('toast'),
    // Global scores
    globalGrade: document.getElementById('global-grade'),
    globalOverallScore: document.getElementById('global-overall-score'),
    globalActivityScore: document.getElementById('global-activity-score'),
    globalActivityBar: document.getElementById('global-activity-bar'),
    globalHealthScore: document.getElementById('global-health-score'),
    globalHealthBar: document.getElementById('global-health-bar'),
    globalQualityScore: document.getElementById('global-quality-score'),
    globalQualityBar: document.getElementById('global-quality-bar'),
    globalDiversityScore: document.getElementById('global-diversity-score'),
    globalDiversityBar: document.getElementById('global-diversity-bar'),
};

// Utility Functions
function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function showToast(message, type = 'success') {
    elements.toast.textContent = message;
    elements.toast.className = `toast ${type}`;
    setTimeout(() => {
        elements.toast.classList.add('hidden');
    }, 3000);
}

function getScoreClass(score) {
    if (score >= 70) return 'score-high';
    if (score >= 40) return 'score-medium';
    return 'score-low';
}

function getGradeClass(grade) {
    if (grade.startsWith('A')) return 'grade-a';
    if (grade.startsWith('B')) return 'grade-b';
    if (grade.startsWith('C')) return 'grade-c';
    if (grade.startsWith('D')) return 'grade-d';
    return 'grade-f';
}

// API Functions
async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API request failed');
        }
        return await response.json();
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        throw error;
    }
}

// Check Ollama Status
async function checkOllamaStatus() {
    elements.ollamaStatus.textContent = 'Checking Ollama...';
    elements.ollamaStatus.className = 'status-badge checking';

    try {
        const status = await fetchAPI('/status/ollama');
        if (status.available) {
            elements.ollamaStatus.textContent = `Ollama: ${status.model}`;
            elements.ollamaStatus.className = 'status-badge online';
        } else {
            elements.ollamaStatus.textContent = 'Ollama Offline';
            elements.ollamaStatus.className = 'status-badge offline';
        }
    } catch (error) {
        elements.ollamaStatus.textContent = 'Ollama Error';
        elements.ollamaStatus.className = 'status-badge offline';
    }
}

// Load Global Stats
async function loadStats() {
    try {
        const stats = await fetchAPI('/stats');
        elements.totalRepos.textContent = formatNumber(stats.total_repositories);
        elements.totalContributors.textContent = formatNumber(stats.total_contributors);
        elements.totalCommits.textContent = formatNumber(stats.total_commits);
        elements.avgQuality.textContent = stats.average_quality_score.toFixed(1);
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Load Global Scores
async function loadGlobalScores() {
    try {
        const data = await fetchAPI('/scores/summary');
        globalScores = data;

        // Update global score display
        const global = data.global;
        elements.globalGrade.textContent = global.grade;
        elements.globalGrade.className = `grade-badge ${getGradeClass(global.grade)}`;
        elements.globalOverallScore.textContent = global.overall_score.toFixed(1);

        // Update score bars (using summary data)
        // For detailed scores, we'd need to call /scores/global
        updateScoreBar('activity', global.overall_score * 0.9); // Approximation
        updateScoreBar('health', global.overall_score * 1.0);
        updateScoreBar('quality', global.overall_score * 0.95);
        updateScoreBar('diversity', global.overall_score * 0.85);

        // Load detailed scores for accuracy
        loadDetailedGlobalScores();

        // Update repository scores grid
        repoScores = data.repositories;
        updateRepoScoresGrid();
        updateRepoScoresChart();

    } catch (error) {
        console.error('Failed to load global scores:', error);
        elements.repoScoresGrid.innerHTML = '<p class="loading">Run analysis to see scores</p>';
    }
}

async function loadDetailedGlobalScores() {
    try {
        const data = await fetchAPI('/scores/global');
        const scores = data.scores;

        elements.globalOverallScore.textContent = scores.overall.toFixed(1);
        updateScoreBar('activity', scores.activity);
        updateScoreBar('health', scores.health);
        updateScoreBar('quality', scores.quality);
        updateScoreBar('diversity', scores.diversity);
    } catch (error) {
        // Silent fail - summary data is sufficient
    }
}

function updateScoreBar(type, value) {
    const scoreEl = document.getElementById(`global-${type}-score`);
    const barEl = document.getElementById(`global-${type}-bar`);

    if (scoreEl) scoreEl.textContent = value.toFixed(1);
    if (barEl) barEl.style.width = `${value}%`;
}

function updateRepoScoresGrid() {
    if (!repoScores || repoScores.length === 0) {
        elements.repoScoresGrid.innerHTML = '<p class="loading">No repository scores available. Run analysis first.</p>';
        return;
    }

    elements.repoScoresGrid.innerHTML = repoScores.map(repo => `
        <div class="repo-score-card">
            <div class="card-header">
                <span class="repo-name">${repo.name}</span>
                <span class="repo-grade ${getGradeClass(repo.grade)}">${repo.grade}</span>
            </div>
            <div class="overall-score">${repo.overall_score.toFixed(1)}</div>
            <div class="mini-scores">
                <div class="mini-score">
                    <span>Commits</span>
                    <span>${formatNumber(repo.commits)}</span>
                </div>
                <div class="mini-score">
                    <span>Contributors</span>
                    <span>${repo.contributors}</span>
                </div>
                <div class="mini-score">
                    <span>Quality</span>
                    <span>${repo.quality_score.toFixed(1)}</span>
                </div>
                <div class="mini-score">
                    <span>Overall</span>
                    <span>${repo.overall_score.toFixed(1)}</span>
                </div>
            </div>
            <div class="card-footer">
                <span>Click to view details</span>
                <button class="btn btn-secondary" onclick="viewRepoScore('${repo.name}')">Details</button>
            </div>
        </div>
    `).join('');
}

async function viewRepoScore(repoName) {
    try {
        const score = await fetchAPI(`/scores/repository/${repoName}`);
        console.log('Repository Score:', score);
        showToast(`${repoName}: ${score.grade} (${score.scores.overall})`);
    } catch (error) {
        showToast(`Failed to load score for ${repoName}`, 'error');
    }
}

// Load Repositories
async function loadRepositories() {
    elements.reposList.innerHTML = '<p class="loading">Loading repositories...</p>';

    try {
        repositories = await fetchAPI('/repositories');

        if (repositories.length === 0) {
            elements.reposList.innerHTML = `
                <p class="loading">No repositories found. Click "Discover Repositories" to scan for repos.</p>
            `;
            return;
        }

        elements.reposList.innerHTML = repositories.map(repo => `
            <div class="repo-card" data-repo="${repo.name}">
                <h3>${repo.name}</h3>
                <div class="stats">
                    <span>${formatNumber(repo.total_commits)} commits</span>
                    <span>${repo.total_contributors} contributors</span>
                    <span>${repo.total_branches} branches</span>
                </div>
                <div class="last-analyzed">
                    ${repo.last_analyzed
                        ? `Last analyzed: ${new Date(repo.last_analyzed).toLocaleDateString()}`
                        : 'Not analyzed yet'}
                </div>
                <div class="actions">
                    <button class="btn btn-primary analyze-btn" data-repo="${repo.name}">
                        Analyze
                    </button>
                    <button class="btn btn-secondary view-btn" data-repo="${repo.name}">
                        View
                    </button>
                </div>
            </div>
        `).join('');

        // Update repo select dropdown
        elements.leaderboardRepoSelect.innerHTML = `
            <option value="">Global (All Repositories)</option>
            ${repositories.map(r => `<option value="${r.name}">${r.name}</option>`).join('')}
        `;

        // Attach event listeners
        document.querySelectorAll('.analyze-btn').forEach(btn => {
            btn.addEventListener('click', () => analyzeRepository(btn.dataset.repo));
        });

    } catch (error) {
        elements.reposList.innerHTML = `<p class="loading">Error loading repositories: ${error.message}</p>`;
    }
}

// Discover Repositories
async function discoverRepositories() {
    elements.discoverBtn.disabled = true;
    elements.discoverBtn.textContent = 'Discovering...';

    try {
        const result = await fetchAPI('/repositories/discover', { method: 'POST' });
        showToast(`Found ${result.count} repositories, registered ${result.registered.length}`);
        await loadRepositories();
    } catch (error) {
        showToast('Failed to discover repositories', 'error');
        console.error('Discover error:', error);
    } finally {
        elements.discoverBtn.disabled = false;
        elements.discoverBtn.textContent = 'Discover Repositories';
    }
}

// Analyze Repository
async function analyzeRepository(repoName) {
    const btn = document.querySelector(`.analyze-btn[data-repo="${repoName}"]`);
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Analyzing...';
    }

    try {
        await fetchAPI(`/repositories/${repoName}/analyze`, { method: 'POST' });
        showToast(`Analysis started for ${repoName}`);
        await loadAnalysisStatus();
    } catch (error) {
        showToast(`Failed to start analysis: ${error.message}`, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Analyze';
        }
    }
}

// Analyze All Repositories
async function analyzeAllRepositories() {
    elements.analyzeAllBtn.disabled = true;
    elements.analyzeAllBtn.textContent = 'Starting...';

    try {
        await fetchAPI('/analyze/all', { method: 'POST' });
        showToast('Analysis started for all repositories');
        await loadAnalysisStatus();
    } catch (error) {
        showToast(`Failed to start analysis: ${error.message}`, 'error');
    } finally {
        elements.analyzeAllBtn.disabled = false;
        elements.analyzeAllBtn.textContent = 'Analyze All Repositories';
    }
}

// Load Leaderboard
async function loadLeaderboard(repoName = '') {
    elements.leaderboardBody.innerHTML = '<tr><td colspan="7" class="loading">Loading leaderboard...</td></tr>';

    try {
        const endpoint = repoName ? `/leaderboard/${repoName}` : '/leaderboard';
        leaderboard = await fetchAPI(endpoint);

        if (leaderboard.length === 0) {
            elements.leaderboardBody.innerHTML = '<tr><td colspan="7" class="loading">No contributors found. Run analysis first.</td></tr>';
            return;
        }

        elements.leaderboardBody.innerHTML = leaderboard.map(entry => `
            <tr>
                <td class="rank rank-${entry.rank}">#${entry.rank}</td>
                <td>
                    <div class="contributor-name">${entry.name}</div>
                    <div class="contributor-email">${entry.email}</div>
                </td>
                <td>${formatNumber(entry.commits)}</td>
                <td>${formatNumber(entry.lines_changed)}</td>
                <td>${entry.prs}</td>
                <td><span class="score-badge ${getScoreClass(entry.quality_score)}">${entry.quality_score}</span></td>
                <td><span class="score-badge ${getScoreClass(entry.impact_score)}">${entry.impact_score}</span></td>
            </tr>
        `).join('');

        // Update contribution chart
        updateContributionChart();

    } catch (error) {
        elements.leaderboardBody.innerHTML = `<tr><td colspan="7" class="loading">Error: ${error.message}</td></tr>`;
    }
}

// Load Analysis Status
async function loadAnalysisStatus() {
    try {
        const data = await fetchAPI('/status');

        if (data.runs.length === 0) {
            elements.analysisStatus.innerHTML = '<p class="loading">No analysis runs yet</p>';
            return;
        }

        elements.analysisStatus.innerHTML = data.runs.map(run => `
            <div class="status-item">
                <div>
                    <strong>Run #${run.id}</strong>
                    <span> - ${run.commits_analyzed} commits analyzed</span>
                </div>
                <div>
                    <span class="status ${run.status}">${run.status}</span>
                </div>
            </div>
        `).join('');

        // If running, poll for updates
        if (data.runs.some(r => r.status === 'running')) {
            setTimeout(loadAnalysisStatus, 5000);
        } else if (data.runs[0]?.status === 'completed') {
            // Refresh data after completion
            loadStats();
            loadRepositories();
            loadLeaderboard();
            loadGlobalScores();
        }

    } catch (error) {
        elements.analysisStatus.innerHTML = `<p class="loading">Error: ${error.message}</p>`;
    }
}

// Update Contribution Chart
function updateContributionChart() {
    if (!leaderboard.length) return;

    const top10 = leaderboard.slice(0, 10);
    const labels = top10.map(e => e.name.split(' ')[0]);
    const commits = top10.map(e => e.commits);

    const ctx = document.getElementById('contribution-chart').getContext('2d');
    if (contributionChart) contributionChart.destroy();

    contributionChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Commits',
                data: commits,
                backgroundColor: 'rgba(99, 102, 241, 0.8)',
                borderColor: 'rgba(99, 102, 241, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });
}

// Update Repository Scores Chart
function updateRepoScoresChart() {
    if (!repoScores || repoScores.length === 0) return;

    const labels = repoScores.map(r => r.name);
    const scores = repoScores.map(r => r.overall_score);
    const quality = repoScores.map(r => r.quality_score);

    const ctx = document.getElementById('repo-scores-chart').getContext('2d');
    if (repoScoresChart) repoScoresChart.destroy();

    repoScoresChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Overall Score',
                    data: scores,
                    backgroundColor: 'rgba(99, 102, 241, 0.8)',
                    borderColor: 'rgba(99, 102, 241, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Quality Score',
                    data: quality,
                    backgroundColor: 'rgba(34, 197, 94, 0.8)',
                    borderColor: 'rgba(34, 197, 94, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#94a3b8' }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });
}

// Event Listeners
elements.analyzeAllBtn.addEventListener('click', analyzeAllRepositories);
elements.discoverBtn.addEventListener('click', discoverRepositories);
elements.leaderboardRepoSelect.addEventListener('change', (e) => {
    loadLeaderboard(e.target.value);
});

// Initialize
async function init() {
    await checkOllamaStatus();
    await loadStats();
    await loadGlobalScores();
    await loadRepositories();
    await loadLeaderboard();
    await loadAnalysisStatus();

    // Periodic refresh
    setInterval(checkOllamaStatus, 30000);
    setInterval(loadStats, 60000);
}

// Start
init();
