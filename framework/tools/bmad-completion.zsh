#!/usr/bin/env zsh
# bmad-completion.zsh — BM-38 : Shell completions pour bmad-init.sh
#
# Installation (zsh) :
#   echo "source /path/to/bmad-custom-kit/framework/tools/bmad-completion.zsh" >> ~/.zshrc
#   source ~/.zshrc
#
# Installation (bash) :
#   # Le fichier bash-completion est à la fin de ce script
#   echo "source /path/to/bmad-custom-kit/framework/tools/bmad-completion.bash" >> ~/.bashrc

# ── Détection du répertoire du kit ──────────────────────────────────────────
_BMAD_KIT_DIR="${BMAD_KIT_DIR:-$(dirname "$(dirname "$(dirname "${(%):-%x}")")")}"

# ── Listage dynamique des archétypes ────────────────────────────────────────
_bmad_archetypes() {
    local archetypes_dir="${_BMAD_KIT_DIR}/archetypes"
    local -a archetypes
    
    # Archétypes principaux
    for d in "${archetypes_dir}"/*/; do
        [[ -d "$d" ]] || continue
        local name
        name="$(basename "$d")"
        [[ "$name" == "meta" || "$name" == "stack" ]] && continue
        archetypes+=("$name")
    done
    
    # Stack agents
    for f in "${archetypes_dir}/stack/agents/"*-expert.md; do
        [[ -f "$f" ]] || continue
        local lang
        lang="$(basename "$f" | sed 's/-expert.md//')"
        archetypes+=("stack/${lang}")
    done
    
    echo "${archetypes[@]}"
}

# ── Listage des checkpoints disponibles ─────────────────────────────────────
_bmad_checkpoints() {
    find "${PWD}/_bmad-output/.runs" -name "state.json" -exec grep -l '"checkpoint_id"' {} \; 2>/dev/null \
        | xargs -I{} sh -c 'grep "checkpoint_id" "$1" | grep -oP "[a-f0-9]{6}"' _ {} 2>/dev/null
}

# ── Listage des branches de session ─────────────────────────────────────────
_bmad_branches() {
    ls -d "${PWD}/_bmad-output/.runs"/*/ 2>/dev/null | xargs -I{} basename {}
}

# ── Completion principale zsh ────────────────────────────────────────────────
_bmad_init_complete() {
    local state
    local -a subcommands
    
    subcommands=(
        'session-branch:Gestion des branches de session'
        'install:Installer un archétype'
        'resume:Reprendre un workflow interrompu'
        'trace:Gérer le BMAD Trace audit trail'
        'doctor:Diagnostic et health check du kit'
        'validate:Valider des fichiers DNA archétype'
        'changelog:Générer CHANGELOG.md depuis BMAD_TRACE'
    )
    
    local context curcontext="$curcontext" line state
    typeset -A opt_args
    
    _arguments -C \
        '1:subcommand:->subcommand' \
        '*::options:->options' \
        '(--help -h)'{--help,-h}'[Afficher l'"'"'aide]' \
        '(--name)--name[Nom du projet]:nom projet:' \
        '(--user)--user[Nom utilisateur]:utilisateur:' \
        '(--lang)--lang[Langue]:langue:(Français English Español Deutsch)' \
        '(--archetype)--archetype[Archétype]:archetype:->archetypes' \
        '(--target)--target[Répertoire cible]:directory:_directories' \
        '(--auto)--auto[Détection automatique]' \
        '(--memory)--memory[Backend mémoire]:backend:(local ollama openai qdrant)' \
        '(--force)--force[Forcer écrasement]' \
        && return
    
    case "$state" in
        subcommand)
            _describe 'sous-commande' subcommands
            ;;
        archetypes)
            local -a arch_list
            arch_list=($(_bmad_archetypes))
            _describe 'archétype' arch_list
            ;;
        options)
            case "${line[1]}" in
                session-branch)
                    _arguments \
                        '--name[Créer une branche]:nom branche:' \
                        '--list[Lister les branches]' \
                        '--diff[Comparer deux branches]:branche:->branches' \
                        '--merge[Merger une branche dans main]:branche:->branches' \
                        '--archive[Archiver une branche]:branche:->branches'
                    ;;
                install)
                    _arguments \
                        '--list[Lister les archétypes disponibles]' \
                        '--archetype[Archétype à installer]:archetype:->archetypes' \
                        '--inspect[Inspecter un archétype]:archetype:->archetypes' \
                        '--target[Répertoire BMAD cible]:directory:_directories' \
                        '--force[Forcer la réinstallation]'
                    case "$state" in
                        archetypes)
                            local -a arch_list
                            arch_list=($(_bmad_archetypes))
                            _describe 'archétype' arch_list
                            ;;
                    esac
                    ;;
                resume)
                    _arguments \
                        '--list[Lister les checkpoints]' \
                        '--checkpoint[Reprendre depuis un checkpoint]:checkpoint_id:->checkpoints'
                    case "$state" in
                        checkpoints)
                            local -a cp_list
                            cp_list=($(_bmad_checkpoints))
                            _describe 'checkpoint' cp_list
                            ;;
                    esac
                    ;;
                trace)
                    _arguments \
                        '--tail[Dernières N entrées]:nombre:(20 50 100)' \
                        '--agent[Filtrer par agent]:agent:(dev qa architect pm sm bmad-master)' \
                        '--type[Filtrer par type]:type:(DECISION REMEMBER HANDOFF CHECKPOINT ACTION ERROR WARN)' \
                        '--branch[Filtrer par session]:branch:->branches' \
                        '--archive[Archiver la trace]' \
                        '--reset[Réinitialiser la trace]' \
                        '--confirm[Confirmer les opérations destructives]'
                    case "$state" in
                        branches)
                            local -a br_list
                            br_list=($(_bmad_branches))
                            _describe 'branche' br_list
                            ;;
                    esac
                    ;;
                doctor)
                    _arguments \
                        '--fix[Corriger automatiquement les problèmes simples]'
                    ;;
                validate)
                    _arguments \
                        '--dna[Fichier DNA à valider]:dna_file:_files -g "*.dna.yaml *.dna.yml"' \
                        '--all[Valider tous les DNA]'
                    ;;
                changelog)
                    _arguments \
                        '--output[Fichier de sortie]:output_file:_files' \
                        '--since[Depuis une date (YYYY-MM-DD)]:date:'
                    ;;
            esac
            ;;
    esac
}

compdef _bmad_init_complete bmad-init.sh
compdef _bmad_init_complete bmad-init

# Alias optionnel pour utilisation raccourcie
if [[ -n "${BMAD_ALIAS:-}" ]]; then
    alias bmad="$_BMAD_KIT_DIR/bmad-init.sh"
    compdef _bmad_init_complete bmad
fi

# ────────────────────────────────────────────────────────────────────────────
# Fichier bash-completion séparé (créer comme bmad-completion.bash)
# ────────────────────────────────────────────────────────────────────────────
# #!/usr/bin/env bash
# # Installation : source /path/to/bmad-completion.bash
#
# _bmad_init_bash() {
#     local cur prev words cword
#     _init_completion || return
#     local subcommands="session-branch install resume trace doctor validate changelog"
#     local archetypes_dir="$(dirname "$0")/../../archetypes"
#
#     case "$prev" in
#         bmad-init.sh|bmad-init)
#             COMPREPLY=($(compgen -W "$subcommands --name --user --lang --archetype --auto --memory --force --help" -- "$cur"))
#             ;;
#         --archetype)
#             local archs=""
#             for d in "$archetypes_dir"/*/; do
#                 archs="$archs $(basename "$d")"
#             done
#             for f in "$archetypes_dir/stack/agents/"*-expert.md; do
#                 archs="$archs stack/$(basename "$f" | sed 's/-expert.md//')"
#             done
#             COMPREPLY=($(compgen -W "$archs" -- "$cur"))
#             ;;
#         --type)
#             COMPREPLY=($(compgen -W "DECISION REMEMBER HANDOFF CHECKPOINT ACTION ERROR WARN" -- "$cur"))
#             ;;
#         --memory)
#             COMPREPLY=($(compgen -W "local ollama openai qdrant" -- "$cur"))
#             ;;
#         *)
#             case "${words[1]}" in
#                 doctor) COMPREPLY=($(compgen -W "--fix" -- "$cur")) ;;
#                 validate) COMPREPLY=($(compgen -W "--dna --all" -- "$cur")) ;;
#                 install) COMPREPLY=($(compgen -W "--list --archetype --inspect --target --force" -- "$cur")) ;;
#                 resume) COMPREPLY=($(compgen -W "--list --checkpoint" -- "$cur")) ;;
#                 trace) COMPREPLY=($(compgen -W "--tail --agent --type --branch --archive --reset --confirm" -- "$cur")) ;;
#                 changelog) COMPREPLY=($(compgen -W "--output --since" -- "$cur")) ;;
#                 session-branch) COMPREPLY=($(compgen -W "--name --list --diff --merge --archive --cherry-pick" -- "$cur")) ;;
#             esac
#             ;;
#     esac
# }
#
# complete -F _bmad_init_bash bmad-init.sh bmad-init bmad
