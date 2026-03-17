import ReactMarkdown from "react-markdown"

interface Props {
  content: string
}

export function Markdown({ content }: Props) {
  return (
    <div className="prose prose-sm max-w-none prose-invert">
      <ReactMarkdown disallowedElements={["script", "iframe", "object", "embed"]}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
