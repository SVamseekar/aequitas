import ReactMarkdown from "react-markdown"

interface Props {
  content: string
}

export function Markdown({ content }: Props) {
  return (
    <div className="prose prose-sm max-w-none prose-neutral text-foreground prose-headings:text-foreground prose-p:text-foreground/90 prose-strong:text-foreground prose-li:text-foreground/90 prose-a:text-primary">
      <ReactMarkdown disallowedElements={["script", "iframe", "object", "embed"]}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
