import { Component } from 'react';
import type { ReactNode, ErrorInfo } from 'react';
import { Box, Button, Heading, Text } from '@chakra-ui/react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box py={20} textAlign="center" px={4}>
          <Heading size="xl" mb={4}>
            Something went wrong
          </Heading>
          <Text color="fg.muted" mb={6} maxW="md" mx="auto">
            An unexpected error occurred. Please try refreshing the page.
          </Text>
          {this.state.error && (
            <Text fontSize="sm" color="red.500" mb={6} fontFamily="mono">
              {this.state.error.message}
            </Text>
          )}
          <Button
            variant="outline"
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.href = '/';
            }}
          >
            Go Home
          </Button>
        </Box>
      );
    }

    return this.props.children;
  }
}
