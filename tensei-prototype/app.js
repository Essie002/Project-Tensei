// ===== PROJECT TENSEI — PROTOTYPE ENGINE =====
// Simulates the EKS CrashLoopBackOff scenario end-to-end

// ===== SUPPORT TIER CONFIGURATION =====
// Change this value to demo different tiers: 'basic', 'developer', 'business', 'enterprise'
const SUPPORT_TIER = 'enterprise';

const TIER_CONFIG = {
    basic: {
        label: 'Basic Support',
        color: '#888',
        contactMethods: [],
        hasEngineer: false,
        hasChat: false,
        hasPhone: false,
        hasEmail: false,
        engineerResponseTime: null,
        description: 'Documentation & community forums only',
        slaNote: 'No technical support included — upgrade for live assistance'
    },
    developer: {
        label: 'Developer Support',
        color: '#4da6ff',
        contactMethods: ['email'],
        hasEngineer: true,
        hasChat: false,
        hasPhone: false,
        hasEmail: true,
        engineerResponseTime: '12–24 hours',
        description: 'Email support during business hours',
        slaNote: 'Engineer response via email within 12–24 hours'
    },
    business: {
        label: 'Business Support',
        color: '#ffc107',
        contactMethods: ['chat', 'phone', 'email'],
        hasEngineer: true,
        hasChat: true,
        hasPhone: true,
        hasEmail: true,
        engineerResponseTime: '~1 hour',
        description: '24/7 chat, phone & email support',
        slaNote: 'Engineer response within 1 hour for critical issues'
    },
    enterprise: {
        label: 'Enterprise Support',
        color: '#ff9900',
        contactMethods: ['chat', 'phone', 'email'],
        hasEngineer: true,
        hasChat: true,
        hasPhone: true,
        hasEmail: true,
        hasTAM: true,
        engineerResponseTime: '~2 minutes',
        description: 'Priority 24/7 support + TAM escalation available',
        slaNote: 'Priority response — engineer within 15 minutes for critical'
    }
};

const currentTier = TIER_CONFIG[SUPPORT_TIER];

// ===== STATE =====
let sessionSeconds = 0;
let scenarioStep = 0;
let timerInterval = null;

// ===== DOM REFS =====
const entryScreen = document.getElementById('entry-screen');
const workspaceScreen = document.getElementById('workspace-screen');
const enterBtn = document.getElementById('enter-workspace-btn');
const chatMessages = document.getElementById('chat-messages');
const quickResponses = document.getElementById('quick-responses');
const trailEntries = document.getElementById('trail-entries');
const trailCount = document.getElementById('trail-count');
const sessionTimer = document.getElementById('session-timer');
const nodeGrid = document.getElementById('node-grid');
const logStream = document.getElementById('log-stream');
const topologyDiagram = document.getElementById('topology-diagram');
const engineerPanel = document.getElementById('engineer-panel');
const engineerAvatar = document.getElementById('engineer-avatar');
const handoverModal = document.getElementById('handover-modal');
const closeHandover = document.getElementById('close-handover');
const contextTabs = document.querySelectorAll('.tab');
const aiStatus = document.getElementById('ai-status');

// ===== ENTRY POINT =====
// Populate entry screen with tier info
(function initEntryScreen() {
    const tierInfo = document.getElementById('entry-tier-info');
    if (tierInfo) {
        const methods = ['Chat', 'Phone', 'Email'];
        const methodBadges = methods.map(m => {
            const key = m.toLowerCase();
            const available = currentTier.contactMethods.includes(key);
            return `<span class="entry-method-badge ${available ? 'available' : 'unavailable'}">${available ? '✓' : '✗'} ${m}</span>`;
        }).join('');

        tierInfo.innerHTML = `
            <div class="entry-tier-label">Detected Support Plan</div>
            <div class="entry-tier-name" style="color:${currentTier.color}">${currentTier.label}</div>
            <div class="entry-tier-desc">${currentTier.description}</div>
            <div class="entry-tier-methods">${methodBadges}</div>
            ${currentTier.hasTAM ? '<div style="font-size:0.65rem; color:var(--text-muted); margin-top:6px;">TAM escalation available via your support engineer</div>' : ''}
        `;
    }
})();

enterBtn.addEventListener('click', () => {
    entryScreen.classList.remove('active');
    workspaceScreen.classList.add('active');
    startSession();
});

closeHandover.addEventListener('click', () => {
    handoverModal.classList.add('hidden');
});

// Tab switching
contextTabs.forEach(tab => {
    tab.addEventListener('click', () => {
        contextTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        document.querySelectorAll('.context-view').forEach(v => v.classList.remove('active'));
        document.getElementById(`view-${tab.dataset.tab}`).classList.add('active');
    });
});

// ===== SESSION START =====
function startSession() {
    // Apply support tier to UI
    applyTierConfig();

    timerInterval = setInterval(() => {
        sessionSeconds++;
        const min = String(Math.floor(sessionSeconds / 60)).padStart(2, '0');
        const sec = String(sessionSeconds % 60).padStart(2, '0');
        sessionTimer.textContent = `${min}:${sec}`;
    }, 1000);

    initClusterView();
    initLogs();
    initTopology();
    runScenario();
}

function applyTierConfig() {
    // Update header badge
    const tierBadge = document.getElementById('support-tier');
    tierBadge.textContent = currentTier.label;
    tierBadge.style.color = currentTier.color;
    tierBadge.style.background = `${currentTier.color}22`;

    // Show/hide contact method buttons
    const contactMethodsEl = document.getElementById('contact-methods');
    if (contactMethodsEl) {
        contactMethodsEl.innerHTML = '';
        if (currentTier.hasChat) {
            contactMethodsEl.innerHTML += '<button class="contact-btn active"><span>💬</span> Chat</button>';
        }
        if (currentTier.hasPhone) {
            contactMethodsEl.innerHTML += '<button class="contact-btn"><span>📞</span> Phone</button>';
        }
        if (currentTier.hasEmail) {
            contactMethodsEl.innerHTML += '<button class="contact-btn"><span>✉️</span> Email</button>';
        }
        if (currentTier.contactMethods.length === 0) {
            contactMethodsEl.innerHTML = '<span class="no-contact">No live support — upgrade your plan for technical assistance</span>';
        }
    }

    // If basic tier, disable chat input and show upgrade message
    if (SUPPORT_TIER === 'basic') {
        document.getElementById('customer-input').disabled = true;
        document.getElementById('customer-input').placeholder = 'Live chat not available on Basic plan';
        document.getElementById('send-btn').disabled = true;
    }
}

// ===== CLUSTER VIEW =====
function initClusterView() {
    const nodes = [
        { name: 'node-1a', status: 'healthy', label: 'Healthy' },
        { name: 'node-1b', status: 'critical', label: 'CrashLoop' },
        { name: 'node-2a', status: 'healthy', label: 'Healthy' },
        { name: 'node-2b', status: 'warning', label: 'High Mem' },
        { name: 'node-3a', status: 'critical', label: 'CrashLoop' },
        { name: 'node-3b', status: 'healthy', label: 'Healthy' },
        { name: 'node-4a', status: 'healthy', label: 'Healthy' },
        { name: 'node-4b', status: 'critical', label: 'CrashLoop' },
    ];

    nodeGrid.innerHTML = nodes.map(n => `
        <div class="node ${n.status}">
            <div class="node-name">${n.name}</div>
            <div class="node-status">${n.label}</div>
        </div>
    `).join('');
}

// ===== LOGS VIEW =====
function initLogs() {
    const redactedLogs = [
        { time: '10:41:02', level: 'error', pod: 'api-server-*****', msg: 'Back-off restarting failed container' },
        { time: '10:41:03', level: 'error', pod: 'api-server-*****', msg: 'ImagePullBackOff: failed to pull image "*****.dkr.ecr.*****.amazonaws.com/api:latest"' },
        { time: '10:41:05', level: 'warn', pod: 'worker-*****', msg: 'Liveness probe failed: connection refused' },
        { time: '10:41:08', level: 'error', pod: 'api-server-*****', msg: 'CrashLoopBackOff: back-off 5m0s restarting failed container' },
        { time: '10:41:12', level: 'info', pod: 'scheduler', msg: 'Successfully assigned default/api-server-***** to node-***' },
        { time: '10:41:15', level: 'error', pod: 'api-server-*****', msg: 'Error: ErrImagePull — 403 Forbidden' },
        { time: '10:41:18', level: 'error', pod: 'worker-*****', msg: 'ImagePullBackOff: authorization failed for ECR registry' },
        { time: '10:41:22', level: 'warn', pod: 'api-server-*****', msg: 'Container runtime: pull access denied, requires IAM ECR permissions' },
        { time: '10:41:25', level: 'error', pod: 'api-server-*****', msg: 'Back-off restarting failed container (restart count: 48)' },
        { time: '10:41:30', level: 'info', pod: 'kubelet', msg: 'Node node-***: memory pressure threshold exceeded' },
        { time: '10:41:33', level: 'error', pod: 'api-server-*****', msg: 'Error: ImagePullBackOff — back-off 2m40s pulling image' },
        { time: '10:41:36', level: 'info', pod: 'kubelet', msg: 'Pulling image "*****.dkr.ecr.*****.amazonaws.com/api:latest"' },
        { time: '10:41:38', level: 'error', pod: 'api-server-*****', msg: 'Failed to pull image: rpc error: code = Unknown desc = 403 Forbidden' },
        { time: '10:41:41', level: 'info', pod: 'endpoint-ctrl', msg: 'Endpoints api-service updated: 0 ready, 3 not ready' },
    ];

    // Add redaction notice at the top
    logStream.innerHTML = '<div class="log-entry system" style="color:var(--accent-orange); margin-bottom:8px; font-style:italic;">⚠️ Logs displayed with redacted identifiers (IPs, ARNs, account IDs masked)</div>';
    logStream.innerHTML += redactedLogs.map(l => `<div class="log-entry">${formatLog(l)}</div>`).join('');
}

function stopLogStreaming() {
    if (logStreamInterval) {
        clearInterval(logStreamInterval);
        logStreamInterval = null;
    }
}

let logStreamInterval = null;

function formatLog(l) {
    return `<span class="timestamp">[${l.time}]</span> <span class="level-${l.level}">${l.level.toUpperCase()}</span> <span class="pod-name">${l.pod}</span> ${l.msg}`;
}

// ===== TOPOLOGY VIEW =====
function initTopology() {
    topologyDiagram.innerHTML = `
        <div class="topo-node ok">
            <div class="topo-label">Application Load Balancer</div>
            <div class="topo-sub">Healthy — forwarding traffic</div>
        </div>
        <div class="topo-arrow">↓</div>
        <div class="topo-node error">
            <div class="topo-label">EKS Pods (api-server)</div>
            <div class="topo-sub">CrashLoopBackOff — ImagePullBackOff</div>
        </div>
        <div class="topo-arrow">↓ image pull</div>
        <div class="topo-node warning">
            <div class="topo-label">Amazon ECR</div>
            <div class="topo-sub">403 Forbidden — IAM permission denied</div>
        </div>
        <div class="topo-arrow">↓ auth</div>
        <div class="topo-node warning">
            <div class="topo-label">IAM Node Role</div>
            <div class="topo-sub">Missing: ecr:GetDownloadUrlForLayer, ecr:BatchGetImage</div>
        </div>
    `;
}

// ===== SCENARIO ENGINE =====
const scenario = [
    // Step 0: AI greets with only alarm metadata (what AWS can see without consent)
    {
        delay: 1000,
        action: 'ai_message',
        text: `Hi — your CloudWatch alarm <code>EKS-PodRestart-Critical</code> triggered 12 minutes ago.<br><br><strong>What I can see (alarm metadata only):</strong><br>1. Alarm state: <span class="highlight">ALARM</span><br>2. Metric: Pod restart count exceeded threshold (>10 in 5 min)<br>3. Cluster: <code>prod-east-1</code><br>4. Time triggered: 10:29 UTC<br><br>To help investigate further, I'd need your permission to view pod logs and cluster details. Would you like to share access?`,
        trail: { text: 'Session started — alarm metadata reviewed (no customer data accessed yet)', actor: 'AI Agent' }
    },
    // Step 1: Quick response options — consent gate
    {
        delay: 500,
        action: 'quick_options',
        options: [
            { text: "Yes, share my logs and cluster data", id: 'consent_full' },
            { text: "Share redacted logs only", id: 'consent_redacted' },
            { text: "I'll share specific things manually", id: 'consent_manual' }
        ]
    },
    // Step 2: Customer grants access
    {
        delay: 0,
        action: 'await_customer',
        trigger: 'consent_full',
        customerText: "Yes, you can access my logs and cluster details.",
        trail: { text: 'Customer granted access: pod logs + cluster configuration', actor: 'Customer', actorClass: 'customer' }
    },
    // Step 3: AI acknowledges consent and begins
    {
        delay: 1500,
        action: 'ai_typing'
    },
    {
        delay: 2500,
        action: 'ai_message',
        text: `Thank you. I now have read access to your pod logs and cluster configuration for this session.<br><br><strong>Access granted:</strong><br>• ✅ CloudWatch Logs (EKS pod logs)<br>• ✅ EKS cluster status (node/pod health)<br>• ✅ IAM role configuration (read-only)<br><br><em>Note: This access is scoped to this session only and will expire when the session ends. I cannot modify anything in your environment.</em><br><br>Based on the logs, I'd like to check three things:<br>1. 🔍 ECR repository permissions<br>2. 🔍 Image tag existence in the registry<br>3. 🔍 Node IAM role configuration<br><br>I'll suggest commands in the Terminal tab for you to run. The results will appear in the Context Panel.`,
        trail: { text: 'Access confirmed — AI reviewing pod logs and cluster config (read-only, session-scoped)', actor: 'AI Agent' }
    },
    // Step 4: First finding
    {
        delay: 3000,
        action: 'ai_typing'
    },
    {
        delay: 2000,
        action: 'ai_message',
        text: `<span class="highlight">Root cause identified.</span><br><br><strong>Problem:</strong> Based on the error logs, your node IAM role (<code>eks-node-role-prod</code>) appears to be missing ECR pull permissions.<br><br><strong>Evidence from logs:</strong><br>1. <code>403 Forbidden</code> responses when pulling from ECR<br>2. <code>ecr:GetDownloadUrlForLayer</code> — permission denied<br>3. <code>ecr:BatchGetImage</code> — permission denied<br><br><strong>Impact:</strong> Nodes cannot authenticate to pull the container image → every pod restart fails with ImagePullBackOff.<br><br>I have a suggested fix ready. Would you like to see it?`,
        trail: { text: 'ROOT CAUSE: Node IAM role missing ECR pull permissions', actor: 'AI Agent' }
    },
    // Step 5: AI found root cause — needs engineer validation before suggesting fix
    {
        delay: 4000,
        action: 'ai_message',
        text: `I've identified a likely root cause. Before I suggest any fix commands, all proposed actions must be validated by a human specialist.<br><br><strong>Your support plan:</strong> ${currentTier.label}<br><strong>Severity:</strong> High (production system impaired)<br><strong>Estimated engineer response:</strong> ${currentTier.engineerResponseTime}<br><br>Connecting you with an available specialist now...`,
        trail: { text: `AI requesting engineer validation — ${currentTier.label}, estimated ${currentTier.engineerResponseTime} response`, actor: 'AI Agent' }
    },
    // Step 6: (handover package generated internally — not shown to customer unless requested)
    {
        delay: 6000,
        action: 'engineer_connecting'
    },
    // Step 7: Engineer joins — realistic wait based on tier
    {
        delay: 8000,
        action: 'engineer_joined',
        trail: { text: 'Sarah K. joined — reviewing AI findings', actor: 'Sarah K.', actorClass: 'engineer' }
    },
    // Step 9: Engineer greets, empathizes, validates AI finding
    {
        delay: 4000,
        action: 'engineer_message',
        text: `Hi there! I'm Sarah, a networking specialist. I know production downtime is stressful — let's get this sorted quickly.<br><br>I've reviewed the AI's analysis and I can confirm the finding is correct:<br><br><strong>✅ Validated:</strong> Your node IAM role (<code>eks-node-role-prod</code>) is missing ECR pull permissions. The <code>403 Forbidden</code> errors in your logs confirm this.<br><br>Let me prepare a fix command for you.<br><br><em><small>Note: I was provided a context summary of this session when I joined — <a href="#" onclick="document.getElementById('handover-modal').classList.remove('hidden'); return false;">view what was shared</a></small></em>`
    },
    // Step 10: Engineer provides validated fix command
    {
        delay: 8000,
        action: 'engineer_message',
        text: `Here's the fix I recommend:<br><br><strong>Command:</strong><br><code>aws iam attach-role-policy --role-name eks-node-role-prod --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly</code><br><br><strong>What it does:</strong><br>1. Attaches the AWS-managed <code>AmazonEC2ContainerRegistryReadOnly</code> policy<br>2. Grants read-only ECR pull permissions to your node role<br>3. No write or delete access — safe for production<br><br>Copy this command and run it in your terminal. Let me know once you've applied it and I'll tell you how to verify.`,
        trail: { text: 'Engineer validated and approved fix: attach ECR policy', actor: 'Sarah K.', actorClass: 'engineer' }
    },
    // Step 10b: Load command into terminal
    {
        delay: 500,
        action: 'suggest_command',
        command: 'aws iam attach-role-policy --role-name eks-node-role-prod --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly',
        source: 'Sarah K. (validated)',
        description: 'Attach ECR read-only policy to node role'
    },
    // Step 11: Quick responses
    {
        delay: 500,
        action: 'quick_options',
        options: [
            { text: "Done — I've run it", id: 'ran_command' },
            { text: "What does this policy include?", id: 'show_policy' }
        ]
    },
    // Step 12: Customer confirms they ran it
    {
        delay: 0,
        action: 'await_customer',
        trigger: 'ran_command',
        customerText: "Done, I've run the command.",
        trail: { text: 'Customer executed: IAM policy attachment', actor: 'Customer', actorClass: 'customer' }
    },
    // Step 13: Update context + engineer monitors
    {
        delay: 2000,
        action: 'update_context',
        contextFn: 'showECRFixApplied'
    },
    {
        delay: 4000,
        action: 'engineer_message',
        text: `Great. Now let's verify it worked. Could you run this and tell me what you see?<br><br><code>kubectl get pods -n default</code><br><br>I want to check if pods are recovering.`,
        trail: { text: 'Engineer requested verification from customer', actor: 'Sarah K.', actorClass: 'engineer' }
    },
    // Step 14: Customer reports result
    {
        delay: 1000,
        action: 'quick_options',
        options: [
            { text: "2 Running, 1 still ImagePullBackOff", id: 'partial_result' },
            { text: "All 3 still failing", id: 'all_failing' }
        ]
    },
    {
        delay: 0,
        action: 'await_customer',
        trigger: 'partial_result',
        customerText: "2 pods are now Running but api-server-a3c21 is still stuck in ImagePullBackOff — getting a timeout error.",
        trail: { text: 'Customer reported: 2/3 recovered, 1 still failing with timeout', actor: 'Customer', actorClass: 'customer' }
    },
    // Update context based on customer's report
    {
        delay: 2000,
        action: 'update_context',
        contextFn: 'showPartialRecovery'
    },
    {
        delay: 4000,
        action: 'engineer_message',
        text: `That confirms what I suspected. The IAM fix resolved 2 of 3 pods, but the timeout on the third tells me it's a network-level block — not permissions.<br><br><strong>My diagnosis:</strong> Your NetworkPolicy is likely restricting outbound traffic and doesn't include the ECR VPC endpoint CIDR. Even with correct IAM, the pod's network can't reach ECR.<br><br>I have a fix. Here it is:`,
        trail: { text: 'Engineer diagnosed: NetworkPolicy blocking ECR endpoint', actor: 'Sarah K.', actorClass: 'engineer' }
    },
    // Step 15: Engineer provides second validated fix
    {
        delay: 6000,
        action: 'engineer_message',
        text: `<strong>Command:</strong><br><code>kubectl patch networkpolicy api-egress -n default --type=json -p '[{"op":"add","path":"/spec/egress/-","value":{"to":[{"ipBlock":{"cidr":"10.0.1.0/24"}}],"ports":[{"port":443,"protocol":"TCP"}]}}]'</code><br><br><strong>What it does:</strong><br>1. Adds an egress rule to your NetworkPolicy<br>2. Allows outbound TCP/443 to <code>10.0.1.0/24</code> (ECR VPC endpoint)<br>3. Only opens that specific CIDR — no broad egress changes<br><br>Copy and paste this into your terminal. Let me know once applied.`
    },
    {
        delay: 500,
        action: 'suggest_command',
        command: "kubectl patch networkpolicy api-egress -n default --type=json -p '[{\"op\":\"add\",\"path\":\"/spec/egress/-\",\"value\":{\"to\":[{\"ipBlock\":{\"cidr\":\"10.0.1.0/24\"}}],\"ports\":[{\"port\":443,\"protocol\":\"TCP\"}]}}]'",
        source: 'Sarah K. (validated)',
        description: 'Add ECR VPC endpoint CIDR to NetworkPolicy egress rules'
    },
    // Step 16: Quick options
    {
        delay: 500,
        action: 'quick_options',
        options: [
            { text: "Done — I've run it", id: 'final_fix' },
            { text: "Explain this command first", id: 'explain_cmd' }
        ]
    },
    // Step 17: Customer confirms
    {
        delay: 0,
        action: 'await_customer',
        trigger: 'final_fix',
        customerText: "Applied. Let me know if it looks good."
    },
    // Step 18: Engineer confirms resolution + summary + docs
    {
        delay: 5000,
        action: 'engineer_message',
        text: `All clear. ✅ All 3 pods are running healthy and pulling images without issues.<br><br><strong>📋 Session Summary:</strong><br><br><strong>What was wrong:</strong><br>1. <strong>Primary:</strong> Node IAM role (<code>eks-node-role-prod</code>) was missing ECR pull permissions<br>2. <strong>Secondary:</strong> NetworkPolicy egress rule was blocking outbound traffic to ECR VPC endpoint<br><br><strong>What was fixed:</strong><br>1. Attached <code>AmazonEC2ContainerRegistryReadOnly</code> policy to the node role<br>2. Patched NetworkPolicy <code>api-egress</code> to allow TCP/443 to <code>10.0.1.0/24</code><br><br><strong>📖 AWS Documentation:</strong><br>• <a href="#">Amazon ECR: Private registry authentication</a><br>• <a href="#">Amazon EKS: Cluster IAM role permissions</a><br>• <a href="#">Kubernetes NetworkPolicy: Egress best practices</a><br><br><strong>💡 Recommendation:</strong> Add ECR VPC endpoint CIDRs to your NetworkPolicy templates to prevent this on future deployments.<br><br>Great working with you — reach out anytime if anything else comes up! 👋`
    },
    {
        delay: 2500,
        action: 'ai_message',
        text: `All pods confirmed healthy. ✅ Application is back online. 🎉<br><br><strong>Session access revoked:</strong> My read access to your logs and cluster data has now expired.<br><br>Is there anything else I can help with?`,
        trail: { text: 'RESOLVED — All pods healthy. Session access revoked.', actor: 'AI Agent' }
    },
    // Step 19: Fix cluster view
    {
        delay: 1000,
        action: 'fix_cluster'
    }
];

// ===== SCENARIO RUNNER =====
let currentScenarioIndex = 0;

function runScenario() {
    processNextStep();
}

function processNextStep() {
    if (currentScenarioIndex >= scenario.length) return;

    const step = scenario[currentScenarioIndex];

    if (step.action === 'await_customer') {
        // Will be triggered by quick response click
        return;
    }

    setTimeout(() => {
        executeStep(step);
        currentScenarioIndex++;
        processNextStep();
    }, step.delay);
}

function executeStep(step) {
    switch (step.action) {
        case 'ai_message':
            removeTypingIndicator();
            // Show typing proportional to message length, then reveal
            showTypingIndicator();
            const aiDelay = getTypingDelay(step.text, 'ai');
            setTimeout(() => {
                removeTypingIndicator();
                addMessage('ai', 'AI Agent', step.text);
                if (step.trail) addTrailEntry(step.trail);
            }, aiDelay);
            break;

        case 'ai_typing':
            showTypingIndicator();
            break;

        case 'customer_message':
            addMessage('customer', 'You', step.text);
            if (step.trail) addTrailEntry(step.trail);
            break;

        case 'quick_options':
            showQuickOptions(step.options);
            break;

        case 'show_handover':
            handoverModal.classList.remove('hidden');
            break;

        case 'engineer_connecting':
            // Reveal the engineer panel and expand the grid
            document.querySelector('.workspace-body').classList.add('with-engineer');
            document.getElementById('resize-handle-2').classList.add('visible');
            engineerPanel.classList.add('visible');
            showEngineerState('connecting');
            aiStatus.textContent = 'Handing over...';
            break;

        case 'engineer_joined':
            showEngineerState('active');
            engineerAvatar.classList.remove('hidden');
            aiStatus.textContent = 'Supporting';
            document.getElementById('engineer-status').textContent = '● Online';
            document.getElementById('engineer-status').style.color = 'var(--accent-green)';
            if (step.trail) addTrailEntry(step.trail);
            break;

        case 'engineer_message':
            // Show engineer typing, then reveal message after proportional delay
            showEngineerTypingIndicator();
            const engDelay = getTypingDelay(step.text, 'engineer');
            setTimeout(() => {
                removeEngineerTypingIndicator();
                addEngineerMessage(step.text);
                if (step.trail) addTrailEntry(step.trail);
            }, engDelay);
            break;

        case 'fix_cluster':
            fixClusterView();
            break;

        case 'update_context':
            if (step.contextFn === 'showECRFixApplied') showECRFixApplied();
            if (step.contextFn === 'showPartialRecovery') showPartialRecovery();
            break;

        case 'suggest_command':
            addSuggestedCommand(step.command, step.source, step.description);
            break;
    }
}

// ===== MESSAGE HELPERS =====

// Calculate realistic delay based on text length (simulates reading/typing time)
// ~40ms per character for AI (fast typer), ~60ms per character for engineer (human speed)
function getTypingDelay(text, type) {
    const plainText = text.replace(/<[^>]*>/g, ''); // strip HTML tags
    const charCount = plainText.length;
    const msPerChar = type === 'engineer' ? 25 : 15;
    const baseDelay = type === 'engineer' ? 2000 : 1500;
    return Math.min(baseDelay + (charCount * msPerChar), 8000); // cap at 8 seconds
}

function addMessage(type, sender, html) {
    const msg = document.createElement('div');
    msg.className = 'message';
    msg.innerHTML = `
        <div class="message-avatar ${type}">${type === 'ai' ? 'AI' : type === 'customer' ? 'Y' : '⚡'}</div>
        <div class="message-body">
            <div class="message-sender">${sender}</div>
            <div class="message-text">${html}</div>
        </div>
    `;
    chatMessages.appendChild(msg);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addMessageWithTyping(type, sender, html, callback) {
    // Show typing indicator first
    showTypingIndicator();
    const delay = getTypingDelay(html, type);
    setTimeout(() => {
        removeTypingIndicator();
        addMessage(type, sender, html);
        if (callback) callback();
    }, delay);
}

function showTypingIndicator() {
    // Remove any existing one first
    removeTypingIndicator();
    const typing = document.createElement('div');
    typing.className = 'message typing-msg';
    typing.innerHTML = `
        <div class="message-avatar ai">AI</div>
        <div class="message-body">
            <div class="typing-indicator"><span></span><span></span><span></span></div>
        </div>
    `;
    chatMessages.appendChild(typing);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showEngineerTypingIndicator() {
    removeEngineerTypingIndicator();
    const chat = document.getElementById('engineer-chat');
    const typing = document.createElement('div');
    typing.className = 'message engineer-typing-msg';
    typing.innerHTML = `
        <div class="message-avatar" style="background: var(--accent-green); color: #fff; width:24px; height:24px; font-size:0.6rem;">SK</div>
        <div class="message-body">
            <div class="typing-indicator"><span></span><span></span><span></span></div>
        </div>
    `;
    chat.appendChild(typing);
    chat.scrollTop = chat.scrollHeight;
}

function removeEngineerTypingIndicator() {
    const chat = document.getElementById('engineer-chat');
    const typing = chat.querySelector('.engineer-typing-msg');
    if (typing) typing.remove();
}

function removeTypingIndicator() {
    const typing = chatMessages.querySelector('.typing-msg');
    if (typing) typing.remove();
}

function showQuickOptions(options) {
    quickResponses.innerHTML = options.map(o =>
        `<button class="quick-btn" data-id="${o.id}">${o.text}</button>`
    ).join('');

    quickResponses.querySelectorAll('.quick-btn').forEach(btn => {
        btn.addEventListener('click', () => handleQuickResponse(btn.dataset.id, btn.textContent));
    });
}

function handleQuickResponse(id, text) {
    quickResponses.innerHTML = '';

    // Add customer message
    addMessage('customer', 'You', text);

    // Handle branching for specific options
    if (id === 'consent_full') {
        // Advance the scenario — full access granted
        const awaitStep = scenario[currentScenarioIndex];
        if (awaitStep && awaitStep.action === 'await_customer') {
            if (awaitStep.trail) addTrailEntry(awaitStep.trail);
            currentScenarioIndex++;
            processNextStep();
        }
        return;
    }

    if (id === 'consent_redacted') {
        addTrailEntry({ text: 'Customer granted access: redacted logs only', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => {
            addMessage('ai', 'AI Agent', `Understood — I'll work with redacted logs. Sensitive data like IP addresses, account IDs, and resource names will be masked.<br><br><strong>Access granted (redacted):</strong><br>• ✅ CloudWatch Logs (redacted — IPs, ARNs masked)<br>• ✅ EKS cluster status (pod state only, no config details)<br><br><em>If I need unredacted data to pinpoint the issue, I'll ask for your permission.</em><br><br>Based on the redacted error patterns, I can see:<br>1. <span class="highlight">47 pod restarts</span> — all with <code>ImagePullBackOff</code><br>2. The errors indicate a <code>403 Forbidden</code> when pulling from ECR<br>3. This points to either an IAM permission or network connectivity issue<br><br>I'll suggest diagnostic commands for your Terminal. Would you like to proceed?`);
            showQuickOptions([
                { text: "Yes, let's investigate", id: 'confirm' },
                { text: "Grant full access instead", id: 'consent_full' }
            ]);
            // Set index to after the consent await step
            currentScenarioIndex = scenario.findIndex(s => s.action === 'await_customer' && s.trigger === 'consent_full') + 1;
        }, 1500);
        return;
    }

    if (id === 'consent_manual') {
        addTrailEntry({ text: 'Customer chose: share data manually', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => {
            addMessage('ai', 'AI Agent', `No problem — you stay in full control. I won't access any data unless you paste it here or run commands in the Terminal.<br><br><strong>How this works:</strong><br>1. I'll suggest what to check and which commands to run<br>2. You run them in the Terminal and I can see the output<br>3. You can also paste log snippets directly in this chat<br><br>To start: could you run <code>kubectl get pods -n default</code> in the Terminal and share the output? That'll tell us which pods are affected.`);
            addSuggestedCommand('kubectl get pods -n default', 'AI Agent', 'List all pods and their current status');
            showQuickOptions([
                { text: "Done — I've run it", id: 'confirm' }
            ]);
            currentScenarioIndex = scenario.findIndex(s => s.action === 'await_customer' && s.trigger === 'consent_full') + 1;
        }, 1500);
        return;
    }

    if (id === 'confirm') {
        // Generic confirm — advance scenario
        const awaitStep = scenario[currentScenarioIndex];
        if (awaitStep && awaitStep.action === 'await_customer') {
            if (awaitStep.trail) addTrailEntry(awaitStep.trail);
            currentScenarioIndex++;
            processNextStep();
        } else {
            // If not at an await step, just move forward
            processNextStep();
        }
        return;
    }

    if (id === 'show') {
        // Customer wants to see what will change before approving
        addTrailEntry({ text: 'Customer requested: show proposed changes', actor: 'Customer', actorClass: 'customer' });
        // Advance the scenario past the await_customer step
        const showAwaitStep = scenario[currentScenarioIndex];
        if (showAwaitStep && showAwaitStep.action === 'await_customer') {
            if (showAwaitStep.trail) addTrailEntry(showAwaitStep.trail);
            currentScenarioIndex++;
            processNextStep();
        }
        return;
    }

    if (id === 'manual') {
        addTrailEntry({ text: 'Customer chose: manual investigation', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => {
            addMessage('ai', 'AI Agent', `No problem. Here's what you need to do:<br><br><strong>Steps to fix:</strong><br>1. Go to <strong>IAM → Roles → eks-node-role-prod</strong><br>2. Click "Attach policies"<br>3. Search for <code>AmazonEC2ContainerRegistryReadOnly</code><br>4. Attach the policy<br>5. Wait 30–60 seconds for pods to retry the image pull<br><br>I'll keep monitoring. Let me know once applied and I'll verify recovery.<br><br><em>Note:</em> I've also identified a potential secondary issue with a NetworkPolicy egress rule (confidence: <span class="highlight">45%</span>). Want me to bring in a networking specialist to verify?`);
            addTrailEntry({ text: 'AI provided manual fix steps — monitoring for recovery', actor: 'AI Agent' });
            showQuickOptions([
                { text: "Yes, bring someone in", id: 'escalate' },
                { text: "Let's wait and see first", id: 'wait' }
            ]);
            currentScenarioIndex = scenario.findIndex(s => s.action === 'await_customer' && s.trigger === 'escalate');
        }, 2000);
        return;
    }

    if (id === 'more') {
        addTrailEntry({ text: 'Customer requested more details on errors', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => showTypingIndicator(), 500);
        setTimeout(() => {
            removeTypingIndicator();
            addMessage('ai', 'AI Agent', `Here's the full breakdown:<br><br><strong>Affected pods (3):</strong><br>1. <code>api-server-7d4f8</code> — CrashLoopBackOff<br>2. <code>api-server-a3c21</code> — CrashLoopBackOff<br>3. <code>worker-bf892</code> — ImagePullBackOff<br><br><strong>Error pattern:</strong><br>• All failing with <code>ImagePullBackOff</code> → nodes cannot download the container image from ECR<br>• Logs show <code>403 Forbidden</code> when pulling from your ECR registry<br><br><strong>Timeline:</strong><br>• Started 12 minutes ago at 10:29<br>• Coincides with a deployment update to <code>prod-east-1</code><br><br>This looks like a permissions issue — the nodes lost the ability to pull images. Want me to dig into the IAM configuration?`);
            showQuickOptions([
                { text: "Yes, investigate", id: 'confirm' },
                { text: "That's my issue, fix it", id: 'confirm' }
            ]);
        }, 2000);
        return;
    }

    if (id === 'other') {
        addTrailEntry({ text: 'Customer indicated a different issue', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => {
            addMessage('ai', 'AI Agent', `Got it — tell me more about what you're experiencing and I'll adjust my investigation.`);
        }, 1000);
        return;
    }

    if (id === 'wait') {
        addTrailEntry({ text: 'Customer chose to wait before escalating', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => {
            addMessage('ai', 'AI Agent', `Understood. I'll keep monitoring pod recovery and flag if the issue persists.`);
        }, 1000);
        setTimeout(() => {
            // Sync: update context panel to show partial recovery
            showPartialRecovery();
            addMessage('ai', 'AI Agent', `<strong>Status update:</strong><br><br>1. ✅ <code>api-server-7d4f8</code> — image pulled successfully, container running<br>2. ✅ <code>worker-bf892</code> — image pulled successfully, container running<br>3. ❌ <code>api-server-a3c21</code> on <code>node-3a</code> — still failing<br><br><strong>Error on failing pod:</strong><br><code>dial tcp 10.0.1.45:443 — connection timed out</code><br><br><strong>Analysis:</strong> This is a network-level block, not a permissions issue. Consistent with a NetworkPolicy egress rule preventing outbound traffic to the ECR VPC endpoint.<br><br>I'd recommend bringing in a networking specialist to confirm. Want me to connect you?`);
            addTrailEntry({ text: 'Partial recovery — 2/3 pods healthy. api-server-a3c21 blocked by NetworkPolicy.', actor: 'AI Agent' });
            showQuickOptions([
                { text: "Yes, bring someone in", id: 'escalate' },
                { text: "I'll investigate myself", id: 'manual_end' }
            ]);
        }, 4000);
        // Set scenario index to the escalation await step
        currentScenarioIndex = scenario.findIndex(s => s.action === 'await_customer' && s.trigger === 'escalate');
        return;
    }

    if (id === 'show_policy') {
        addTrailEntry({ text: 'Customer requested policy details', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => {
            addMessage('ai', 'AI Agent', `The <code>AmazonEC2ContainerRegistryReadOnly</code> policy grants:\n\n• <code>ecr:GetDownloadUrlForLayer</code>\n• <code>ecr:BatchGetImage</code>\n• <code>ecr:GetAuthorizationToken</code>\n• <code>ecr:BatchCheckLayerAvailability</code>\n• <code>ecr:DescribeRepositories</code>\n\n<strong>Scope:</strong> Read-only. No ability to push, delete, or modify images. Safe to apply to node roles.\n\nGo ahead and run the command in the Terminal when you're ready.`);
            showQuickOptions([
                { text: "Done — I've run it", id: 'ran_command' }
            ]);
        }, 1500);
        return;
    }

    if (id === 'explain_cmd') {
        addTrailEntry({ text: 'Customer requested command explanation', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => {
            addEngineerMessage(`Sure! Here's what that kubectl patch does:\n\n• <strong>Target:</strong> NetworkPolicy named "api-egress" in the default namespace\n• <strong>Action:</strong> Adds a new egress rule allowing outbound TCP/443 to the CIDR 10.0.1.0/24\n• <strong>Why 10.0.1.0/24:</strong> That's your VPC endpoint range for ECR — the pod needs to reach that IP to pull images\n• <strong>Effect:</strong> Only opens port 443 to that specific CIDR. No broad egress changes.\n\nIt's safe to run. Let me know once applied.`);
            showQuickOptions([
                { text: "Done — I've run it", id: 'final_fix' }
            ]);
        }, 1500);
        return;
    }

    if (id === 'ran_command' || id === 'partial_result' || id === 'all_failing') {
        // Advance to the next step (same as confirming fix)
        const awaitStep = scenario[currentScenarioIndex];
        if (awaitStep && awaitStep.action === 'await_customer') {
            if (awaitStep.trail) addTrailEntry(awaitStep.trail);
            currentScenarioIndex++;
            processNextStep();
        }
        return;
    }

    if (id === 'manual_end') {
        addTrailEntry({ text: 'Customer chose to investigate independently', actor: 'Customer', actorClass: 'customer' });
        setTimeout(() => {
            addMessage('ai', 'AI Agent', `No problem. I've loaded a diagnostic command into your Terminal: <code>kubectl describe pod api-server-a3c21 -n default</code>. Check the Terminal tab.\n\nI'll stay here if you need me. Just let me know.`);
            addSuggestedCommand('kubectl describe pod api-server-a3c21 -n default', 'AI Agent', 'Inspect failing pod events and status');
        }, 1000);
        return;
    }

    // Default: advance the scenario normally
    const awaitStep = scenario[currentScenarioIndex];
    if (awaitStep && awaitStep.action === 'await_customer') {
        if (awaitStep.trail) addTrailEntry(awaitStep.trail);
        currentScenarioIndex++;
        processNextStep();
    }
}

// ===== ENGINEER HELPERS =====
function showEngineerState(state) {
    document.querySelectorAll('.engineer-state').forEach(s => s.classList.add('hidden'));
    document.getElementById(`eng-state-${state}`).classList.remove('hidden');
}

function addEngineerMessage(text) {
    const chat = document.getElementById('engineer-chat');
    const msg = document.createElement('div');
    msg.className = 'message';
    msg.innerHTML = `
        <div class="message-avatar" style="background: var(--accent-green); color: #fff; width:24px; height:24px; font-size:0.6rem;">SK</div>
        <div class="message-body">
            <div class="message-sender">Sarah K.</div>
            <div class="message-text">${text}</div>
        </div>
    `;
    chat.appendChild(msg);
    chat.scrollTop = chat.scrollHeight;
}

// ===== TRAIL HELPERS =====
let trailCountNum = 0;
function addTrailEntry(entry) {
    trailCountNum++;
    trailCount.textContent = `${trailCountNum} events`;

    const time = new Date();
    const timeStr = `${String(time.getHours()).padStart(2,'0')}:${String(time.getMinutes()).padStart(2,'0')}`;

    const el = document.createElement('div');
    el.className = 'trail-entry';
    el.innerHTML = `
        <div class="trail-entry-time">${timeStr}</div>
        <div class="trail-entry-text">${entry.text}</div>
        <div class="trail-entry-actor ${entry.actorClass || ''}">${entry.actor}</div>
    `;
    trailEntries.appendChild(el);
    trailEntries.scrollLeft = trailEntries.scrollWidth;
}

// ===== CONTEXT PANEL SYNC FUNCTIONS =====
// Update cluster to show partial recovery (2 healthy, 1 still failing)
function showPartialRecovery() {
    const nodes = [
        { name: 'node-1a', status: 'healthy', label: 'Healthy' },
        { name: 'node-1b', status: 'healthy', label: 'Recovered' },
        { name: 'node-2a', status: 'healthy', label: 'Healthy' },
        { name: 'node-2b', status: 'healthy', label: 'Recovered' },
        { name: 'node-3a', status: 'critical', label: 'CrashLoop' },
        { name: 'node-3b', status: 'healthy', label: 'Healthy' },
        { name: 'node-4a', status: 'healthy', label: 'Healthy' },
        { name: 'node-4b', status: 'healthy', label: 'Healthy' },
    ];

    nodeGrid.innerHTML = nodes.map(n => `
        <div class="node ${n.status}">
            <div class="node-name">${n.name}</div>
            <div class="node-status">${n.label}</div>
        </div>
    `).join('');

    document.getElementById('restart-count').textContent = '3';
    document.getElementById('restart-count').className = 'stat-value warning';
    document.querySelector('.cluster-status').textContent = '● Degraded';
    document.querySelector('.cluster-status').style.color = 'var(--accent-yellow)';
    document.querySelector('.cluster-status').style.background = 'rgba(255,193,7,0.15)';

    // Switch logs to show partial recovery
    switchToPartialRecoveryLogs();
}

// Switch log stream to show partial recovery state
function switchToPartialRecoveryLogs() {
    stopLogStreaming();

    // Replace logs with static redacted partial recovery view
    logStream.innerHTML = '<div class="log-entry system" style="color:var(--accent-orange); margin-bottom:8px; font-style:italic;">⚠️ Logs displayed with redacted identifiers (IPs, ARNs, account IDs masked)</div>';

    const recoveryLogs = [
        { time: '10:45:01', level: 'info', pod: 'api-server-*****', msg: 'Successfully pulled image — container starting' },
        { time: '10:45:02', level: 'info', pod: 'worker-*****', msg: 'Successfully pulled image — container starting' },
        { time: '10:45:05', level: 'error', pod: 'api-server-*****', msg: 'ImagePullBackOff: dial tcp ***.***.***.***:443 — connection timed out' },
        { time: '10:45:08', level: 'warn', pod: 'api-server-*****', msg: 'NetworkPolicy egress: packet dropped to ***.***.***.***:443 (ECR endpoint)' },
        { time: '10:45:12', level: 'error', pod: 'api-server-*****', msg: 'Back-off restarting failed container — network egress blocked' },
        { time: '10:45:15', level: 'info', pod: 'endpoint-ctrl', msg: 'Endpoints api-service updated: 2 ready, 1 not ready' },
    ];

    logStream.innerHTML += recoveryLogs.map(l => `<div class="log-entry">${formatLog(l)}</div>`).join('');
}

// Update cluster after AI applies the ECR fix (before escalation question)
function showECRFixApplied() {
    // Update restart count to show it's decreasing
    document.getElementById('restart-count').textContent = '12';
    document.getElementById('restart-count').className = 'stat-value warning';

    // Add a success log entry
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = formatLog({ time, level: 'info', pod: 'iam-watcher', msg: 'Policy AmazonEC2ContainerRegistryReadOnly attached to role eks-node-role-prod' });
    logStream.appendChild(entry);
    logStream.scrollTop = logStream.scrollHeight;

    // Update topology to show ECR is now accessible
    topologyDiagram.innerHTML = `
        <div class="topo-node ok">
            <div class="topo-label">Application Load Balancer</div>
            <div class="topo-sub">Healthy — forwarding traffic</div>
        </div>
        <div class="topo-arrow">↓</div>
        <div class="topo-node warning">
            <div class="topo-label">EKS Pods (api-server)</div>
            <div class="topo-sub">2/3 recovering — 1 still failing (network timeout)</div>
        </div>
        <div class="topo-arrow">↓ image pull</div>
        <div class="topo-node ok">
            <div class="topo-label">Amazon ECR</div>
            <div class="topo-sub">✅ IAM permissions fixed — pull authorized</div>
        </div>
        <div class="topo-arrow">↓ network</div>
        <div class="topo-node error">
            <div class="topo-label">NetworkPolicy (Egress)</div>
            <div class="topo-sub">⚠️ Blocking outbound to ECR VPC endpoint CIDR</div>
        </div>
    `;
}

// ===== FIX CLUSTER VIEW =====
function fixClusterView() {
    // Stop the error log stream
    stopLogStreaming();

    // Add resolution logs
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
    const resolutionLogs = [
        { time, level: 'info', pod: 'api-server-7d4f8', msg: 'Successfully pulled image "123456789.dkr.ecr.us-east-1.amazonaws.com/api:latest"' },
        { time, level: 'info', pod: 'api-server-a3c21', msg: 'Started container api-server' },
        { time, level: 'info', pod: 'worker-bf892', msg: 'Started container worker' },
        { time, level: 'info', pod: 'endpoint-ctrl', msg: 'Endpoints api-service updated: 3 ready, 0 not ready' },
    ];
    resolutionLogs.forEach(l => {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        entry.innerHTML = formatLog(l);
        logStream.appendChild(entry);
    });
    logStream.scrollTop = logStream.scrollHeight;

    const nodes = [
        { name: 'node-1a', status: 'healthy', label: 'Healthy' },
        { name: 'node-1b', status: 'healthy', label: 'Recovered' },
        { name: 'node-2a', status: 'healthy', label: 'Healthy' },
        { name: 'node-2b', status: 'healthy', label: 'Recovered' },
        { name: 'node-3a', status: 'healthy', label: 'Recovered' },
        { name: 'node-3b', status: 'healthy', label: 'Healthy' },
        { name: 'node-4a', status: 'healthy', label: 'Healthy' },
        { name: 'node-4b', status: 'healthy', label: 'Recovered' },
    ];

    nodeGrid.innerHTML = nodes.map(n => `
        <div class="node ${n.status}">
            <div class="node-name">${n.name}</div>
            <div class="node-status">${n.label}</div>
        </div>
    `).join('');

    document.getElementById('restart-count').textContent = '0';
    document.getElementById('restart-count').className = 'stat-value';
    document.querySelector('.cluster-status').textContent = '● Healthy';
    document.querySelector('.cluster-status').className = 'cluster-status';
    document.querySelector('.cluster-status').style.color = 'var(--accent-green)';
    document.querySelector('.cluster-status').style.background = 'rgba(76,175,80,0.15)';
}

// ===== MANUAL INPUT =====
document.getElementById('send-btn').addEventListener('click', sendCustomerMessage);
document.getElementById('customer-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendCustomerMessage();
});

function sendCustomerMessage() {
    const input = document.getElementById('customer-input');
    const text = input.value.trim();
    if (!text) return;

    addMessage('customer', 'You', text);
    input.value = '';

    // If we're waiting for customer input, advance scenario
    const awaitStep = scenario[currentScenarioIndex];
    if (awaitStep && awaitStep.action === 'await_customer') {
        if (awaitStep.trail) addTrailEntry(awaitStep.trail);
        quickResponses.innerHTML = '';
        currentScenarioIndex++;
        processNextStep();
    }
}


// ===== SANDBOX TERMINAL =====
const terminalOutput = document.getElementById('terminal-output');
const terminalInput = document.getElementById('terminal-input');
const terminalRunBtn = document.getElementById('terminal-run-btn');
const suggestedCommandsEl = document.getElementById('suggested-commands');

function addSuggestedCommand(command, source, description) {
    const cmdEl = document.createElement('div');
    cmdEl.className = 'suggested-cmd';
    cmdEl.innerHTML = `
        <div style="flex:1">
            <div class="suggested-cmd-text">${command}</div>
            <div style="font-size:0.65rem; color:var(--text-muted); margin-top:4px;">${description}</div>
        </div>
        <span class="suggested-cmd-source">${source}</span>
        <span class="suggested-cmd-status pending">Pending</span>
    `;
    cmdEl.addEventListener('click', () => {
        // Load command into terminal input
        terminalInput.value = command;
        // Switch to terminal tab
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelector('[data-tab="terminal"]').classList.add('active');
        document.querySelectorAll('.context-view').forEach(v => v.classList.remove('active'));
        document.getElementById('view-terminal').classList.add('active');
        // Mark as loaded
        cmdEl.querySelector('.suggested-cmd-status').textContent = 'Loaded';
        cmdEl.querySelector('.suggested-cmd-status').className = 'suggested-cmd-status approved';
        // Flash the terminal tab
        document.querySelector('[data-tab="terminal"]').style.background = 'var(--accent-green)';
        setTimeout(() => {
            document.querySelector('[data-tab="terminal"]').style.background = '';
        }, 1000);
    });
    suggestedCommandsEl.appendChild(cmdEl);

    // Keep terminal tab lit until customer clicks it
    const termTab = document.querySelector('[data-tab="terminal"]');
    termTab.classList.add('tab-alert');
    termTab.style.background = 'var(--accent-orange)';
    termTab.style.color = '#000';

    // Only stop flashing when customer clicks the terminal tab
    const clearAlert = () => {
        termTab.classList.remove('tab-alert');
        termTab.style.background = '';
        termTab.style.color = '';
        termTab.removeEventListener('click', clearAlert);
    };
    termTab.addEventListener('click', clearAlert);
}

// Simulated terminal command execution
const terminalResponses = {
    'aws iam attach-role-policy': [
        { type: 'output', text: 'Attaching policy to role eks-node-role-prod...' },
        { type: 'success', text: '✓ Policy AmazonEC2ContainerRegistryReadOnly attached successfully.' },
        { type: 'output', text: 'Effective immediately. Pods will retry image pull on next restart cycle.' },
    ],
    'kubectl patch networkpolicy': [
        { type: 'output', text: 'networkpolicy.networking.k8s.io/api-egress patched' },
        { type: 'success', text: '✓ Egress rule added: allow TCP/443 to 10.0.1.0/24 (ECR VPC endpoint)' },
        { type: 'output', text: 'Pods affected: api-server-a3c21 (will retry on next cycle)' },
    ],
    'kubectl get pods': [
        { type: 'output', text: 'NAME                    READY   STATUS             RESTARTS   AGE' },
        { type: 'output', text: 'api-server-7d4f8        1/1     Running            48         2h' },
        { type: 'output', text: 'api-server-a3c21        0/1     ImagePullBackOff   52         2h' },
        { type: 'output', text: 'worker-bf892            1/1     Running            12         2h' },
    ],
    'kubectl describe pod': [
        { type: 'output', text: 'Events:' },
        { type: 'output', text: '  Warning  Failed     2m   kubelet  Failed to pull image: dial tcp 10.0.1.45:443 — connection timed out' },
        { type: 'output', text: '  Warning  Failed     1m   kubelet  Back-off pulling image' },
        { type: 'error', text: '  Normal   BackOff    30s  kubelet  Back-off restarting failed container' },
    ],
};

function runTerminalCommand(command) {
    if (!command.trim()) return;

    // Show the command
    const cmdLine = document.createElement('div');
    cmdLine.className = 'terminal-line command';
    cmdLine.textContent = command;
    terminalOutput.appendChild(cmdLine);

    // Find matching response
    let response = null;
    for (const key of Object.keys(terminalResponses)) {
        if (command.includes(key)) {
            response = terminalResponses[key];
            break;
        }
    }

    if (response) {
        // Simulate delayed output
        response.forEach((line, i) => {
            setTimeout(() => {
                const el = document.createElement('div');
                el.className = `terminal-line ${line.type}`;
                el.textContent = line.text;
                terminalOutput.appendChild(el);
                terminalOutput.scrollTop = terminalOutput.scrollHeight;
            }, 500 + (i * 400));
        });
    } else {
        setTimeout(() => {
            const el = document.createElement('div');
            el.className = 'terminal-line error';
            el.textContent = `command not found: ${command.split(' ')[0]}`;
            terminalOutput.appendChild(el);
            terminalOutput.scrollTop = terminalOutput.scrollHeight;
        }, 300);
    }

    // Update suggested command status if it matches
    suggestedCommandsEl.querySelectorAll('.suggested-cmd').forEach(cmd => {
        const cmdText = cmd.querySelector('.suggested-cmd-text').textContent;
        if (command.includes(cmdText.substring(0, 30)) || cmdText.includes(command.substring(0, 30))) {
            cmd.querySelector('.suggested-cmd-status').textContent = 'Executed';
            cmd.querySelector('.suggested-cmd-status').className = 'suggested-cmd-status run';
        }
    });

    terminalInput.value = '';
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

terminalRunBtn.addEventListener('click', () => runTerminalCommand(terminalInput.value));
terminalInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') runTerminalCommand(terminalInput.value);
});

// ===== RESIZABLE PANELS =====
function initResize() {
    const handle1 = document.getElementById('resize-handle-1');
    const handle2 = document.getElementById('resize-handle-2');
    const chatPanel = document.getElementById('panel-chat');
    const contextPanel = document.getElementById('panel-context');
    const engineerPanelEl = document.getElementById('engineer-panel');
    const workspaceBody = document.getElementById('workspace-body');

    let isResizing = false;
    let currentHandle = null;

    function startResize(handle) {
        return function(e) {
            isResizing = true;
            currentHandle = handle;
            handle.classList.add('active');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            e.preventDefault();
        };
    }

    handle1.addEventListener('mousedown', startResize(handle1));
    handle2.addEventListener('mousedown', startResize(handle2));

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;

        const bodyRect = workspaceBody.getBoundingClientRect();
        const mouseX = e.clientX - bodyRect.left;
        const totalWidth = bodyRect.width;

        if (currentHandle === handle1) {
            // Resizing between chat and context
            const chatWidth = Math.max(200, Math.min(mouseX - 2, totalWidth * 0.6));
            chatPanel.style.flex = 'none';
            chatPanel.style.width = chatWidth + 'px';
        } else if (currentHandle === handle2) {
            // Resizing between context and engineer
            const engineerWidth = Math.max(200, Math.min(totalWidth - mouseX - 2, totalWidth * 0.5));
            engineerPanelEl.style.flex = 'none';
            engineerPanelEl.style.width = engineerWidth + 'px';
        }
    });

    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            if (currentHandle) currentHandle.classList.remove('active');
            currentHandle = null;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }
    });
}

initResize();
